"""Compare evaluation outcomes for two harness configuration versions."""

from app.schemas import (
    EvaluationResult,
    ExecutionTrace,
    MetricComparison,
    OperationalMetrics,
    RegressionDecision,
)


def compare_versions(
    baseline_evaluations: list[EvaluationResult],
    candidate_evaluations: list[EvaluationResult],
    *,
    baseline_traces: list[ExecutionTrace] | None = None,
    candidate_traces: list[ExecutionTrace] | None = None,
) -> RegressionDecision:
    """Compare the same test set using explicit correctness transition rules."""

    baseline, baseline_version = _index_evaluations(
        baseline_evaluations, "baseline"
    )
    candidate, candidate_version = _index_evaluations(
        candidate_evaluations, "candidate"
    )
    if baseline_version == candidate_version:
        raise ValueError("Baseline and candidate versions must be distinct")
    if baseline.keys() != candidate.keys():
        missing_candidate = sorted(baseline.keys() - candidate.keys())
        missing_baseline = sorted(candidate.keys() - baseline.keys())
        raise ValueError(
            "Baseline and candidate test ID sets must match; "
            f"missing from candidate={missing_candidate}, "
            f"missing from baseline={missing_baseline}"
        )

    improved: list[str] = []
    regressed: list[str] = []
    unchanged_pass: list[str] = []
    unchanged_fail: list[str] = []
    for test_id in sorted(baseline):
        baseline_passed = baseline[test_id].passed
        candidate_passed = candidate[test_id].passed
        if not baseline_passed and candidate_passed:
            improved.append(test_id)
        elif baseline_passed and not candidate_passed:
            regressed.append(test_id)
        elif baseline_passed:
            unchanged_pass.append(test_id)
        else:
            unchanged_fail.append(test_id)

    baseline_count = sum(item.passed for item in baseline.values())
    candidate_count = sum(item.passed for item in candidate.values())
    total = len(baseline)
    baseline_rate = baseline_count / total
    candidate_rate = candidate_count / total
    decision, explanation = _decision(improved, regressed)

    baseline_metrics, candidate_metrics = _optional_trace_metrics(
        baseline_traces,
        candidate_traces,
        expected_test_ids=set(baseline),
        baseline_version=baseline_version,
        candidate_version=candidate_version,
    )

    return RegressionDecision(
        baseline_version=baseline_version,
        candidate_version=candidate_version,
        baseline_pass_count=baseline_count,
        candidate_pass_count=candidate_count,
        baseline_total=total,
        candidate_total=total,
        baseline_pass_rate=baseline_rate,
        candidate_pass_rate=candidate_rate,
        improved_test_ids=improved,
        regressed_test_ids=regressed,
        unchanged_pass_test_ids=unchanged_pass,
        unchanged_fail_test_ids=unchanged_fail,
        comparisons=[
            MetricComparison(
                metric="pass_rate",
                v1=baseline_rate,
                v2=candidate_rate,
                delta=candidate_rate - baseline_rate,
            )
        ],
        primary_metric_improved=candidate_rate > baseline_rate,
        critical_regression_detected=bool(regressed),
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        decision=decision,
        explanation=explanation,
    )


def summarize_execution_traces(
    traces: list[ExecutionTrace],
) -> OperationalMetrics:
    """Summarize trace observations without applying decision thresholds."""

    if not traces:
        raise ValueError("ExecutionTrace collection must not be empty")
    latencies = [
        trace.latency_seconds
        for trace in traces
        if trace.latency_seconds is not None
    ]
    total_tool_calls = sum(len(trace.tool_calls) for trace in traces)
    return OperationalMetrics(
        average_latency_seconds=(
            sum(latencies) / len(latencies) if latencies else None
        ),
        total_tool_calls=total_tool_calls,
        average_tool_calls=total_tool_calls / len(traces),
        execution_error_count=sum(trace.error is not None for trace in traces),
    )


def _index_evaluations(
    evaluations: list[EvaluationResult], label: str
) -> tuple[dict[str, EvaluationResult], str]:
    if not evaluations:
        raise ValueError(f"{label.capitalize()} evaluations must not be empty")
    versions = {evaluation.agent_version for evaluation in evaluations}
    if len(versions) != 1:
        raise ValueError(f"{label.capitalize()} evaluations contain mixed versions")

    indexed: dict[str, EvaluationResult] = {}
    for evaluation in evaluations:
        if evaluation.test_id in indexed:
            raise ValueError(
                f"Duplicate test_id in {label} evaluations: {evaluation.test_id!r}"
            )
        indexed[evaluation.test_id] = evaluation
    return indexed, versions.pop()


def _optional_trace_metrics(
    baseline_traces: list[ExecutionTrace] | None,
    candidate_traces: list[ExecutionTrace] | None,
    *,
    expected_test_ids: set[str],
    baseline_version: str,
    candidate_version: str,
) -> tuple[OperationalMetrics | None, OperationalMetrics | None]:
    if (baseline_traces is None) != (candidate_traces is None):
        raise ValueError("Baseline and candidate traces must be provided together")
    if baseline_traces is None or candidate_traces is None:
        return None, None
    _validate_traces(
        baseline_traces, expected_test_ids, baseline_version, "baseline"
    )
    _validate_traces(
        candidate_traces, expected_test_ids, candidate_version, "candidate"
    )
    return (
        summarize_execution_traces(baseline_traces),
        summarize_execution_traces(candidate_traces),
    )


def _validate_traces(
    traces: list[ExecutionTrace],
    expected_test_ids: set[str],
    expected_version: str,
    label: str,
) -> None:
    trace_ids: set[str] = set()
    for trace in traces:
        if trace.test_id in trace_ids:
            raise ValueError(f"Duplicate test_id in {label} traces: {trace.test_id!r}")
        trace_ids.add(trace.test_id)
        if trace.agent_version != expected_version:
            raise ValueError(
                f"{label.capitalize()} trace version {trace.agent_version!r} "
                f"does not match evaluations version {expected_version!r}"
            )
    if trace_ids != expected_test_ids:
        raise ValueError(f"{label.capitalize()} trace test ID set does not match evaluations")


def _decision(
    improved_test_ids: list[str], regressed_test_ids: list[str]
) -> tuple[str, str]:
    if regressed_test_ids:
        return (
            "reject",
            "Candidate introduced one or more PASS-to-FAIL correctness regressions.",
        )
    if improved_test_ids:
        return (
            "accept",
            "Candidate improved at least one failed test with no correctness regressions.",
        )
    return (
        "review",
        "Candidate produced no correctness regressions but demonstrated no improvements.",
    )
