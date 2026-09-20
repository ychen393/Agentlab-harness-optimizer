"""Deterministically group failed executions by their primary observable failure."""

from collections import defaultdict

from app.schemas import EvaluationResult, ExecutionTrace, FailurePattern


_CATEGORY_ORDER = (
    "workflow_step_limit",
    "execution_error",
    "tool_usage_failure",
    "rule_failure",
)
_TOOL_USAGE_METRICS = frozenset(
    {"required_tool_called", "correct_tool_sequence", "tool_usage"}
)
_SUMMARIES = {
    "workflow_step_limit": (
        "Multi-step workflows are blocked by the configured workflow step limit."
    ),
    "execution_error": "Target executions failed with an unexpected error.",
    "tool_usage_failure": (
        "Executions completed but required tool usage or tool order was incorrect."
    ),
    "rule_failure": "Executions failed deterministic evaluation rules.",
}


def analyze_failures(
    evaluations: list[EvaluationResult],
    traces: list[ExecutionTrace],
) -> list[FailurePattern]:
    """Return deterministic patterns for failed evaluation/trace pairs."""

    trace_by_identity = _index_traces(traces)
    grouped_test_ids: dict[str, list[str]] = defaultdict(list)

    for evaluation in evaluations:
        if evaluation.passed:
            continue

        identity = (evaluation.test_id, evaluation.agent_version)
        trace = trace_by_identity.get(identity)
        if trace is None:
            raise ValueError(
                "No ExecutionTrace matches failed EvaluationResult identity "
                f"test_id={evaluation.test_id!r}, "
                f"agent_version={evaluation.agent_version!r}"
            )

        category = _primary_category(evaluation, trace)
        grouped_test_ids[category].append(evaluation.test_id)

    patterns: list[FailurePattern] = []
    for category in _CATEGORY_ORDER:
        test_ids = grouped_test_ids.get(category)
        if not test_ids:
            continue
        affected_test_ids = sorted(set(test_ids))
        count = len(test_ids)
        patterns.append(
            FailurePattern(
                id=f"F{len(patterns) + 1}",
                category=category,
                count=count,
                affected_test_ids=affected_test_ids,
                severity=_severity(category, count),
                summary=_SUMMARIES[category],
            )
        )

    return patterns


def _index_traces(
    traces: list[ExecutionTrace],
) -> dict[tuple[str, str], ExecutionTrace]:
    indexed: dict[tuple[str, str], ExecutionTrace] = {}
    for trace in traces:
        identity = (trace.test_id, trace.agent_version)
        if identity in indexed:
            raise ValueError(
                "Duplicate ExecutionTrace identity "
                f"test_id={trace.test_id!r}, agent_version={trace.agent_version!r}"
            )
        indexed[identity] = trace
    return indexed


def _primary_category(
    evaluation: EvaluationResult, trace: ExecutionTrace
) -> str:
    if trace.error is not None:
        if _is_workflow_step_limit(trace.error):
            return "workflow_step_limit"
        return "execution_error"

    failed_metrics = {
        metric for metric, score in evaluation.rule_scores.items() if score < 1.0
    }
    if failed_metrics & _TOOL_USAGE_METRICS:
        return "tool_usage_failure"
    return "rule_failure"


def _is_workflow_step_limit(error: str) -> bool:
    normalized = error.casefold()
    return "max_steps" in normalized and (
        "workflow" in normalized or "step" in normalized
    )


def _severity(category: str, count: int) -> str:
    if category in {"workflow_step_limit", "execution_error"} and count > 1:
        return "high"
    return "medium"
