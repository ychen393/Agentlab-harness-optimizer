"""Tests for deterministic, evidence-backed root-cause analysis."""

import pytest
from pydantic import ValidationError

from app.debugger import analyze_failures, analyze_root_cause
from app.runner import run_agent
from app.schemas import (
    ExecutionTrace,
    FailurePattern,
    RootCauseAnalysis,
)
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    commerce_v1_config,
    evaluate_commerce,
)


def workflow_pattern(*test_ids: str) -> FailurePattern:
    return FailurePattern(
        id="F1",
        category="workflow_step_limit",
        count=len(test_ids),
        affected_test_ids=list(test_ids),
        severity="high",
        summary="Workflow step limit blocked execution.",
    )


def limited_trace(test_id: str, *, version: str = "commerce-v1") -> ExecutionTrace:
    return ExecutionTrace(
        test_id=test_id,
        agent_version=version,
        output='{"error": "step limit"}',
        tool_calls=["search_policy"],
        error=(
            "workflow.max_steps=2 cannot execute workflow step 3 "
            "for check_eligibility"
        ),
    )


def test_workflow_step_limit_produces_evidence_backed_workflow_diagnosis() -> None:
    analysis = analyze_root_cause(
        workflow_pattern("T1", "T2"),
        [limited_trace("T1"), limited_trace("T2")],
        commerce_v1_config(),
    )

    assert isinstance(analysis, RootCauseAnalysis)
    assert analysis.target_component == "workflow_config"
    assert "step budget is insufficient" in analysis.root_cause
    assert any("T1 executed tool calls" in item for item in analysis.evidence)
    assert any("T2 executed tool calls" in item for item in analysis.evidence)
    assert any("workflow.max_steps=2" in item for item in analysis.evidence)
    assert 0.0 <= analysis.confidence <= 1.0


def test_real_commerce_pipeline_produces_expected_root_cause() -> None:
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
    patterns = analyze_failures(evaluations, traces)

    analysis = analyze_root_cause(patterns[0], traces, config)

    assert patterns[0].affected_test_ids == ["CT6", "CT7"]
    assert analysis.failure_category == "workflow_step_limit"
    assert analysis.target_component == "workflow_config"
    assert "multi-step workflows" in analysis.root_cause
    assert any("CT6" in item and "search_policy" in item for item in analysis.evidence)
    assert any("CT7" in item and "search_policy" in item for item in analysis.evidence)
    assert any("max_steps=2" in item for item in analysis.evidence)


def test_unrelated_traces_are_ignored() -> None:
    analysis = analyze_root_cause(
        workflow_pattern("T1"),
        [limited_trace("UNRELATED"), limited_trace("T1")],
        commerce_v1_config(),
    )

    assert all("UNRELATED" not in item for item in analysis.evidence)


def test_missing_affected_trace_is_rejected() -> None:
    with pytest.raises(ValueError, match="Missing affected ExecutionTrace"):
        analyze_root_cause(
            workflow_pattern("T1", "T2"),
            [limited_trace("T1")],
            commerce_v1_config(),
        )


def test_duplicate_relevant_trace_is_rejected() -> None:
    duplicate = limited_trace("T1")

    with pytest.raises(ValueError, match="Duplicate ExecutionTrace identity"):
        analyze_root_cause(
            workflow_pattern("T1"),
            [duplicate, duplicate.model_copy()],
            commerce_v1_config(),
        )


def test_trace_for_other_agent_version_does_not_match() -> None:
    with pytest.raises(ValueError, match="commerce-v1"):
        analyze_root_cause(
            workflow_pattern("T1"),
            [limited_trace("T1", version="commerce-v2")],
            commerce_v1_config(),
        )


def test_inputs_are_not_mutated() -> None:
    pattern = workflow_pattern("T1")
    traces = [limited_trace("T1")]
    config = commerce_v1_config()
    pattern_snapshot = pattern.model_copy(deep=True)
    traces_snapshot = [trace.model_copy(deep=True) for trace in traces]
    config_snapshot = config.model_copy(deep=True)

    analyze_root_cause(pattern, traces, config)

    assert pattern == pattern_snapshot
    assert traces == traces_snapshot
    assert config == config_snapshot


def test_step_limit_pattern_requires_matching_trace_evidence() -> None:
    trace = limited_trace("T1").model_copy(update={"error": "provider unavailable"})

    with pytest.raises(ValueError, match="lacks matching max_steps evidence"):
        analyze_root_cause(workflow_pattern("T1"), [trace], commerce_v1_config())


def test_unsupported_category_does_not_fabricate_diagnosis() -> None:
    pattern = FailurePattern(
        id="F2",
        category="rule_failure",
        count=1,
        affected_test_ids=["T1"],
        severity="medium",
        summary="A rule failed.",
    )

    with pytest.raises(ValueError, match="Unsupported failure category"):
        analyze_root_cause(pattern, [limited_trace("T1")], commerce_v1_config())


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_root_cause_confidence_must_be_normalized(confidence: float) -> None:
    with pytest.raises(ValidationError):
        RootCauseAnalysis(
            failure_category="workflow_step_limit",
            evidence=["Evidence"],
            root_cause="Cause",
            target_component="workflow_config",
            confidence=confidence,
        )
