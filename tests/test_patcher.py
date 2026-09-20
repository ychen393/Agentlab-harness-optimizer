"""Tests for safe HarnessPatch application and config version creation."""

import pytest
from pydantic import ValidationError

from app.debugger import analyze_failures, analyze_root_cause
from app.optimizer import apply_harness_patch, propose_harness_patch
from app.runner import run_agent
from app.schemas import HarnessPatch
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    commerce_v1_config,
    evaluate_commerce,
)


def real_patch_inputs():
    config = commerce_v1_config()
    agent = CommerceAgent()
    traces = [
        run_agent(scenario.test_case, config, agent)
        for scenario in COMMERCE_SCENARIOS
    ]
    evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(COMMERCE_SCENARIOS, traces, strict=True)
    ]
    pattern = analyze_failures(evaluations, traces)[0]
    root_cause = analyze_root_cause(pattern, traces, config)
    patch = propose_harness_patch(pattern, root_cause, config)
    return config, patch


def test_real_pipeline_creates_separate_commerce_v2_config() -> None:
    v1, patch = real_patch_inputs()
    v1_snapshot = v1.model_copy(deep=True)
    patch_snapshot = patch.model_copy(deep=True)

    v2 = apply_harness_patch(v1, patch, "commerce-v2")

    assert v2 is not v1
    assert v2.version == "commerce-v2"
    assert v2.workflow.max_steps == 3
    assert v1.version == "commerce-v1"
    assert v1.workflow.max_steps == 2
    assert v1 == v1_snapshot
    assert patch == patch_snapshot
    assert v2.system_prompt == v1.system_prompt
    assert v2.tools == v1.tools
    assert v2.context == v1.context
    assert v2.workflow.require_citation == v1.workflow.require_citation


def test_stale_patch_is_rejected() -> None:
    v1, patch = real_patch_inputs()
    stale = patch.model_copy(update={"old_value": {"max_steps": 1}})

    with pytest.raises(ValueError, match="Stale HarnessPatch"):
        apply_harness_patch(v1, stale, "commerce-v2")


@pytest.mark.parametrize("new_version", ["", "   ", "commerce-v1"])
def test_invalid_or_duplicate_version_is_rejected(new_version: str) -> None:
    v1, patch = real_patch_inputs()

    with pytest.raises(ValueError, match="new_version"):
        apply_harness_patch(v1, patch, new_version)


def test_invalid_proposed_workflow_value_is_rejected() -> None:
    v1, patch = real_patch_inputs()
    invalid = patch.model_copy(update={"proposed_value": {"max_steps": 0}})

    with pytest.raises(ValidationError):
        apply_harness_patch(v1, invalid, "commerce-v2")


def test_malformed_system_prompt_patch_is_rejected() -> None:
    v1, patch = real_patch_inputs()
    unsupported = patch.model_copy(update={"target_component": "system_prompt"})

    with pytest.raises(ValueError, match="only system_prompt"):
        apply_harness_patch(v1, unsupported, "commerce-v2")


def test_non_editable_component_is_rejected_even_if_model_is_bypassed() -> None:
    v1, patch = real_patch_inputs()
    unsafe = HarnessPatch.model_construct(
        **{
            **patch.model_dump(),
            "target_component": "commerce_agent_source",
        }
    )

    with pytest.raises(ValueError, match="not editable"):
        apply_harness_patch(v1, unsafe, "commerce-v2")


def test_workflow_patch_cannot_modify_unrelated_workflow_fields() -> None:
    v1, patch = real_patch_inputs()
    broad = patch.model_copy(
        update={
            "old_value": {"max_steps": 2, "require_citation": False},
            "proposed_value": {"max_steps": 3, "require_citation": True},
        }
    )

    with pytest.raises(ValueError, match="only workflow.max_steps"):
        apply_harness_patch(v1, broad, "commerce-v2")
