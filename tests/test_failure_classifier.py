"""Tests for deterministic, domain-independent failure classification."""

import pytest

from app.debugger import analyze_failures
from app.runner import run_agent
from app.schemas import EvaluationResult, ExecutionTrace, FailurePattern
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    commerce_v1_config,
    evaluate_commerce,
)


def evaluation(
    test_id: str,
    *,
    passed: bool = False,
    rule_scores: dict[str, float] | None = None,
    agent_version: str = "v1",
) -> EvaluationResult:
    return EvaluationResult(
        test_id=test_id,
        agent_version=agent_version,
        passed=passed,
        final_score=1.0 if passed else 0.0,
        rule_scores=rule_scores or {},
        semantic_scores={},
        failed_requirement_ids=[] if passed else ["R1"],
        explanation="passed" if passed else "failed",
    )


def trace(
    test_id: str,
    *,
    error: str | None = None,
    agent_version: str = "v1",
) -> ExecutionTrace:
    return ExecutionTrace(
        test_id=test_id,
        agent_version=agent_version,
        output="output",
        error=error,
    )


def test_all_pass_evaluations_return_no_patterns() -> None:
    assert analyze_failures([evaluation("T1", passed=True)], []) == []


def test_real_commerce_baseline_groups_cascading_failures_once() -> None:
    config = commerce_v1_config()
    agent = CommerceAgent()
    traces = [
        run_agent(scenario.test_case, config, agent)
        for scenario in COMMERCE_SCENARIOS
    ]
    evaluations = [
        evaluate_commerce(scenario, execution)
        for scenario, execution in zip(COMMERCE_SCENARIOS, traces, strict=True)
    ]

    patterns = analyze_failures(evaluations, traces)

    assert patterns == [
        FailurePattern(
            id="F1",
            category="workflow_step_limit",
            count=2,
            affected_test_ids=["CT6", "CT7"],
            severity="high",
            summary=(
                "Multi-step workflows are blocked by the configured workflow "
                "step limit."
            ),
        )
    ]


def test_other_execution_error_forms_separate_pattern() -> None:
    evaluations = [
        evaluation("T_WORKFLOW"),
        evaluation("T_EXECUTION"),
    ]
    traces = [
        trace("T_WORKFLOW", error="workflow.max_steps=2 blocks step 3"),
        trace("T_EXECUTION", error="provider unavailable"),
    ]

    patterns = analyze_failures(evaluations, traces)

    assert [pattern.category for pattern in patterns] == [
        "workflow_step_limit",
        "execution_error",
    ]
    assert [pattern.id for pattern in patterns] == ["F1", "F2"]


def test_successful_execution_with_tool_rule_failure_is_tool_usage_failure() -> None:
    patterns = analyze_failures(
        [evaluation("T1", rule_scores={"required_tool_called": 0.0})],
        [trace("T1")],
    )

    assert len(patterns) == 1
    assert patterns[0].category == "tool_usage_failure"


def test_other_deterministic_failure_uses_rule_fallback() -> None:
    patterns = analyze_failures(
        [evaluation("T1", rule_scores={"valid_json": 0.0})],
        [trace("T1")],
    )

    assert patterns[0].category == "rule_failure"


def test_ids_and_ordering_are_deterministic_regardless_of_input_order() -> None:
    evaluations = [
        evaluation("T_RULE", rule_scores={"valid_json": 0.0}),
        evaluation("T_TOOL", rule_scores={"correct_tool_sequence": 0.0}),
        evaluation("T_EXEC"),
    ]
    traces = [
        trace("T_TOOL"),
        trace("T_EXEC", error="runtime failed"),
        trace("T_RULE"),
    ]

    forward = analyze_failures(evaluations, traces)
    reversed_result = analyze_failures(
        list(reversed(evaluations)), list(reversed(traces))
    )

    assert forward == reversed_result
    assert [pattern.id for pattern in forward] == ["F1", "F2", "F3"]
    assert [pattern.category for pattern in forward] == [
        "execution_error",
        "tool_usage_failure",
        "rule_failure",
    ]


def test_missing_trace_for_failed_evaluation_is_explicit() -> None:
    with pytest.raises(ValueError, match="No ExecutionTrace matches"):
        analyze_failures([evaluation("T_MISSING")], [])


def test_duplicate_trace_identity_is_rejected() -> None:
    duplicate = trace("T1")

    with pytest.raises(ValueError, match="Duplicate ExecutionTrace identity"):
        analyze_failures([evaluation("T1")], [duplicate, duplicate.model_copy()])


def test_trace_matching_uses_test_id_and_agent_version() -> None:
    with pytest.raises(ValueError, match="agent_version='v1'"):
        analyze_failures(
            [evaluation("T1", agent_version="v1")],
            [trace("T1", agent_version="v2")],
        )
