"""Evidence-backed deterministic root-cause analysis for known failure patterns."""

from app.schemas import (
    AgentConfig,
    ExecutionTrace,
    FailurePattern,
    RootCauseAnalysis,
)


def analyze_root_cause(
    failure_pattern: FailurePattern,
    traces: list[ExecutionTrace],
    agent_config: AgentConfig,
) -> RootCauseAnalysis:
    """Diagnose one supported pattern without proposing a configuration change."""

    if failure_pattern.category not in {"workflow_step_limit", "tool_usage_failure"}:
        raise ValueError(
            "Unsupported failure category for deterministic root-cause analysis: "
            f"{failure_pattern.category!r}"
        )

    relevant_traces = _select_relevant_traces(
        failure_pattern, traces, agent_config.version
    )
    if failure_pattern.category == "tool_usage_failure":
        return _analyze_tool_usage_failure(
            failure_pattern, relevant_traces, agent_config
        )

    for trace in relevant_traces:
        if not _has_step_limit_evidence(trace.error):
            raise ValueError(
                "FailurePattern category workflow_step_limit lacks matching "
                f"max_steps evidence for test_id={trace.test_id!r}"
            )

    evidence: list[str] = []
    for trace in relevant_traces:
        called_tools = ", ".join(trace.tool_calls) or "none"
        evidence.append(
            f"{trace.test_id} executed tool calls before failure: {called_tools}."
        )
        evidence.append(f"{trace.test_id} execution error: {trace.error}")
    evidence.append(
        "Current AgentConfig "
        f"{agent_config.version!r} sets workflow.max_steps="
        f"{agent_config.workflow.max_steps}."
    )

    return RootCauseAnalysis(
        failure_category=failure_pattern.category,
        evidence=evidence,
        root_cause=(
            "The configured workflow step budget is insufficient for the observed "
            "multi-step workflows, which complete an earlier tool call but are "
            "blocked before the next required workflow step."
        ),
        target_component="workflow_config",
        confidence=0.99,
    )


def _analyze_tool_usage_failure(
    failure_pattern: FailurePattern,
    relevant_traces: list[ExecutionTrace],
    agent_config: AgentConfig,
) -> RootCauseAnalysis:
    if any(trace.error is not None for trace in relevant_traces):
        raise ValueError(
            "Tool-usage root cause requires successful executions with incorrect "
            "tool selection, not execution errors"
        )
    if any(not trace.tool_calls for trace in relevant_traces):
        raise ValueError(
            "Tool-usage root cause lacks observed tool-call evidence"
        )

    evidence = [
        (
            f"{trace.test_id} completed with observed tool calls: "
            f"{', '.join(trace.tool_calls)}."
        )
        for trace in relevant_traces
    ]
    evidence.append(
        f"FailurePattern {failure_pattern.id} classifies these completed "
        "executions as incorrect required-tool usage."
    )
    evidence.append(
        f"Current system_prompt is {agent_config.system_prompt!r}."
    )
    return RootCauseAnalysis(
        failure_category=failure_pattern.category,
        evidence=evidence,
        root_cause=(
            "The observed router completed execution with the wrong tool, while "
            "the current system prompt gives only generic routing guidance and "
            "does not instruct the router to honor explicit exclusions or "
            "negated intent when product and promotion language coexist."
        ),
        target_component="system_prompt",
        confidence=0.9,
    )


def _select_relevant_traces(
    failure_pattern: FailurePattern,
    traces: list[ExecutionTrace],
    agent_version: str,
) -> list[ExecutionTrace]:
    affected_ids = set(failure_pattern.affected_test_ids)
    indexed: dict[str, ExecutionTrace] = {}

    for trace in traces:
        if trace.test_id not in affected_ids or trace.agent_version != agent_version:
            continue
        if trace.test_id in indexed:
            raise ValueError(
                "Duplicate ExecutionTrace identity makes root-cause evidence "
                f"ambiguous for test_id={trace.test_id!r}, "
                f"agent_version={agent_version!r}"
            )
        indexed[trace.test_id] = trace

    missing_ids = affected_ids - indexed.keys()
    if missing_ids:
        raise ValueError(
            "Missing affected ExecutionTrace records for AgentConfig version "
            f"{agent_version!r}: {sorted(missing_ids)}"
        )

    return [indexed[test_id] for test_id in sorted(affected_ids)]


def _has_step_limit_evidence(error: str | None) -> bool:
    if error is None:
        return False
    normalized = error.casefold()
    return "max_steps" in normalized and (
        "workflow" in normalized or "step" in normalized
    )
