"""Tests for evidence-backed bounded HarnessPatch proposals."""

import pytest
from pydantic import ValidationError

from app.debugger import analyze_failures, analyze_root_cause
from app.optimizer import propose_harness_patch
from app.runner import run_agent
from app.schemas import FailurePattern, HarnessPatch, RootCauseAnalysis
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    commerce_v1_config,
    evaluate_commerce,
)


def real_pipeline_inputs():
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
    return pattern, root_cause, config


def test_real_f1_proposes_bounded_workflow_patch() -> None:
    pattern, root_cause, config = real_pipeline_inputs()

    patch = propose_harness_patch(pattern, root_cause, config)

    assert isinstance(patch, HarnessPatch)
    assert patch.target_component == "workflow_config"
    assert patch.old_value == {"max_steps": 2}
    assert patch.proposed_value == {"max_steps": 3}
    assert patch.supporting_failure_pattern_ids == ["F1"]
    assert "search_policy" in patch.expected_effect
    assert "check_eligibility" in patch.expected_effect
    assert "Expected" in patch.expected_effect
    assert patch.regression_risk


def test_patch_proposal_does_not_mutate_inputs() -> None:
    pattern, root_cause, config = real_pipeline_inputs()
    pattern_snapshot = pattern.model_copy(deep=True)
    root_cause_snapshot = root_cause.model_copy(deep=True)
    config_snapshot = config.model_copy(deep=True)

    propose_harness_patch(pattern, root_cause, config)

    assert pattern == pattern_snapshot
    assert root_cause == root_cause_snapshot
    assert config == config_snapshot


def test_proposal_requires_blocked_step_evidence() -> None:
    pattern, root_cause, config = real_pipeline_inputs()
    root_cause = root_cause.model_copy(update={"evidence": ["No step evidence"]})

    with pytest.raises(ValueError, match="lacks concrete blocked"):
        propose_harness_patch(pattern, root_cause, config)


def test_mismatched_failure_and_root_cause_are_rejected() -> None:
    pattern, root_cause, config = real_pipeline_inputs()
    root_cause = root_cause.model_copy(update={"failure_category": "other"})

    with pytest.raises(ValueError, match="does not match"):
        propose_harness_patch(pattern, root_cause, config)


def test_harness_patch_requires_supporting_failure_id() -> None:
    with pytest.raises(ValidationError):
        HarnessPatch(
            target_component="workflow_config",
            old_value={"max_steps": 2},
            proposed_value={"max_steps": 3},
            reason="Evidence-backed reason",
            supporting_failure_pattern_ids=[],
            expected_effect="Expected effect",
            regression_risk="Bounded risk",
        )


def test_unsupported_root_cause_component_is_rejected() -> None:
    pattern = FailurePattern(
        id="F1",
        category="workflow_step_limit",
        count=1,
        affected_test_ids=["T1"],
        severity="medium",
        summary="Step limit",
    )
    root_cause = RootCauseAnalysis(
        failure_category="workflow_step_limit",
        evidence=["T1 blocked at workflow step 3"],
        root_cause="Prompt issue",
        target_component="system_prompt",
        confidence=0.5,
    )

    with pytest.raises(ValueError, match="Unsupported target component"):
        propose_harness_patch(pattern, root_cause, commerce_v1_config())
