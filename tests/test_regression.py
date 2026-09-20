"""Tests for deterministic harness regression execution and comparison."""

import pytest

from app.debugger import analyze_failures, analyze_root_cause
from app.optimizer import apply_harness_patch, propose_harness_patch
from app.regression import compare_versions
from app.runner import run_agent
from app.schemas import EvaluationResult
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    commerce_v1_config,
    evaluate_commerce,
)


def evaluation(test_id: str, passed: bool, version: str) -> EvaluationResult:
    return EvaluationResult(
        test_id=test_id,
        agent_version=version,
        passed=passed,
        final_score=1.0 if passed else 0.0,
        rule_scores={},
        semantic_scores={},
        failed_requirement_ids=[] if passed else ["R1"],
        explanation="passed" if passed else "failed",
    )


def test_all_outcome_transitions_and_counts_are_classified() -> None:
    baseline = [
        evaluation("T_IMPROVED", False, "v1"),
        evaluation("T_REGRESSED", True, "v1"),
        evaluation("T_PASS", True, "v1"),
        evaluation("T_FAIL", False, "v1"),
    ]
    candidate = [
        evaluation("T_FAIL", False, "v2"),
        evaluation("T_PASS", True, "v2"),
        evaluation("T_REGRESSED", False, "v2"),
        evaluation("T_IMPROVED", True, "v2"),
    ]

    result = compare_versions(baseline, candidate)

    assert result.improved_test_ids == ["T_IMPROVED"]
    assert result.regressed_test_ids == ["T_REGRESSED"]
    assert result.unchanged_pass_test_ids == ["T_PASS"]
    assert result.unchanged_fail_test_ids == ["T_FAIL"]
    assert result.baseline_pass_count == 2
    assert result.candidate_pass_count == 2
    assert result.baseline_pass_rate == 0.5
    assert result.candidate_pass_rate == 0.5
    assert result.decision == "reject"


def test_improvement_without_regression_is_accepted() -> None:
    result = compare_versions(
        [evaluation("T1", False, "v1")],
        [evaluation("T1", True, "v2")],
    )

    assert result.decision == "accept"
    assert result.primary_metric_improved is True
    assert result.critical_regression_detected is False


def test_no_change_is_reviewed() -> None:
    result = compare_versions(
        [evaluation("T1", True, "v1")],
        [evaluation("T1", True, "v2")],
    )

    assert result.decision == "review"


def test_comparison_is_independent_of_input_order() -> None:
    baseline = [evaluation("T2", False, "v1"), evaluation("T1", True, "v1")]
    candidate = [evaluation("T1", True, "v2"), evaluation("T2", True, "v2")]

    forward = compare_versions(baseline, candidate)
    reversed_result = compare_versions(
        list(reversed(baseline)), list(reversed(candidate))
    )

    assert forward == reversed_result


def test_missing_test_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="test ID sets must match"):
        compare_versions(
            [evaluation("T1", True, "v1")],
            [evaluation("T2", True, "v2")],
        )


@pytest.mark.parametrize("side", ["baseline", "candidate"])
def test_duplicate_test_ids_are_rejected(side: str) -> None:
    baseline = [evaluation("T1", True, "v1")]
    candidate = [evaluation("T1", True, "v2")]
    if side == "baseline":
        baseline.append(evaluation("T1", False, "v1"))
    else:
        candidate.append(evaluation("T1", False, "v2"))

    with pytest.raises(ValueError, match="Duplicate test_id"):
        compare_versions(baseline, candidate)


@pytest.mark.parametrize("side", ["baseline", "candidate"])
def test_mixed_versions_are_rejected(side: str) -> None:
    baseline = [evaluation("T1", True, "v1"), evaluation("T2", True, "v1")]
    candidate = [evaluation("T1", True, "v2"), evaluation("T2", True, "v2")]
    if side == "baseline":
        baseline[1] = evaluation("T2", True, "other")
    else:
        candidate[1] = evaluation("T2", True, "other")

    with pytest.raises(ValueError, match="mixed versions"):
        compare_versions(baseline, candidate)


def test_identical_versions_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be distinct"):
        compare_versions(
            [evaluation("T1", True, "v1")],
            [evaluation("T1", True, "v1")],
        )


def test_evaluation_inputs_are_not_mutated() -> None:
    baseline = [evaluation("T1", False, "v1")]
    candidate = [evaluation("T1", True, "v2")]
    baseline_snapshot = [item.model_copy(deep=True) for item in baseline]
    candidate_snapshot = [item.model_copy(deep=True) for item in candidate]

    compare_versions(baseline, candidate)

    assert baseline == baseline_snapshot
    assert candidate == candidate_snapshot


def test_real_pipeline_derives_decision_from_actual_v1_and_v2_results() -> None:
    scenarios_snapshot = [scenario.model_copy(deep=True) for scenario in COMMERCE_SCENARIOS]
    v1 = commerce_v1_config()
    v1_snapshot = v1.model_copy(deep=True)
    agent = CommerceAgent()

    v1_traces = [run_agent(s.test_case, v1, agent) for s in COMMERCE_SCENARIOS]
    v1_evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(COMMERCE_SCENARIOS, v1_traces, strict=True)
    ]
    pattern = analyze_failures(v1_evaluations, v1_traces)[0]
    root_cause = analyze_root_cause(pattern, v1_traces, v1)
    patch = propose_harness_patch(pattern, root_cause, v1)
    v2 = apply_harness_patch(v1, patch, "commerce-v2")
    v2_snapshot = v2.model_copy(deep=True)

    v2_traces = [run_agent(s.test_case, v2, agent) for s in COMMERCE_SCENARIOS]
    v2_evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(COMMERCE_SCENARIOS, v2_traces, strict=True)
    ]
    v1_trace_snapshot = [trace.model_copy(deep=True) for trace in v1_traces]
    v2_trace_snapshot = [trace.model_copy(deep=True) for trace in v2_traces]
    result = compare_versions(
        v1_evaluations,
        v2_evaluations,
        baseline_traces=v1_traces,
        candidate_traces=v2_traces,
    )

    expected_decision = (
        "reject"
        if result.regressed_test_ids
        else "accept"
        if result.improved_test_ids
        else "review"
    )
    assert result.decision == expected_decision
    assert {item.test_id for item in v1_evaluations} == {
        scenario.test_case.id for scenario in COMMERCE_SCENARIOS
    }
    assert {item.test_id for item in v2_evaluations} == {
        scenario.test_case.id for scenario in COMMERCE_SCENARIOS
    }
    assert result.baseline_metrics is not None
    assert result.candidate_metrics is not None
    assert result.baseline_metrics.total_tool_calls == sum(
        len(trace.tool_calls) for trace in v1_traces
    )
    assert result.candidate_metrics.total_tool_calls == sum(
        len(trace.tool_calls) for trace in v2_traces
    )
    assert result.baseline_metrics.execution_error_count == sum(
        trace.error is not None for trace in v1_traces
    )
    assert result.candidate_metrics.execution_error_count == sum(
        trace.error is not None for trace in v2_traces
    )
    assert v1_traces == v1_trace_snapshot
    assert v2_traces == v2_trace_snapshot
    assert v1 == v1_snapshot
    assert v2 == v2_snapshot
    assert list(COMMERCE_SCENARIOS) == scenarios_snapshot
