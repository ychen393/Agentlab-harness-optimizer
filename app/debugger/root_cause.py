"""Evidence-backed deterministic root-cause analysis for known failure patterns."""

from app.schemas import (
    AgentConfig,
    ExecutionTrace,
    FailurePattern,
    RootCauseAnalysis,
)
from .tool_arguments import (
    argument_contract_parts,
    find_tool_contract,
    validate_tool_arguments,
)
from .instruction_constraints import find_instruction_violation


def analyze_root_cause(
    failure_pattern: FailurePattern,
    traces: list[ExecutionTrace],
    agent_config: AgentConfig,
) -> RootCauseAnalysis:
    """Diagnose one supported pattern without proposing a configuration change."""

    if failure_pattern.category not in {
        "workflow_step_limit",
        "tool_usage_failure",
        "tool_argument_schema_failure",
    }:
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
    if failure_pattern.category == "tool_argument_schema_failure":
        return _analyze_tool_argument_schema_failure(
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

    violations = [
        find_instruction_violation(trace, agent_config) for trace in relevant_traces
    ]
    if all(violation is not None for violation in violations):
        constraint, observed_behavior_key = violations[0]
        observed_behavior = constraint.forbidden_behavior
        evidence = [
            f"constraint id: {constraint.id}",
                f"condition: {constraint.condition}",
                f"observed behavior: {observed_behavior}",
                f"observed behavior key: {observed_behavior_key}",
            f"required behavior: {constraint.required_behavior}",
            f"forbidden behavior: {constraint.forbidden_behavior}",
        ]
        return RootCauseAnalysis(
            failure_category=failure_pattern.category,
            evidence=evidence,
            root_cause=(
                "The observed behavior violates a registered instruction "
                "constraint, and the current system prompt does not encode that "
                "constraint clearly enough."
            ),
            target_component="system_prompt",
            confidence=0.99,
            metadata={
                "constraint_id": constraint.id,
                "condition": constraint.condition,
                "required_behavior": constraint.required_behavior,
                "forbidden_behavior": constraint.forbidden_behavior,
                "observed_behavior": observed_behavior,
                "observed_behavior_key": observed_behavior_key,
                "instruction_lead": constraint.instruction_lead,
                "rationale": constraint.rationale,
            },
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
            "the current system prompt does not provide sufficient guidance for "
            "the required tool-selection behavior."
        ),
        target_component="system_prompt",
        confidence=0.9,
    )


def _analyze_tool_argument_schema_failure(
    failure_pattern: FailurePattern,
    relevant_traces: list[ExecutionTrace],
    agent_config: AgentConfig,
) -> RootCauseAnalysis:
    observations: list[dict[str, object]] = []
    evidence: list[str] = []
    for trace in relevant_traces:
        if not trace.tool_calls or not trace.tool_call_arguments:
            raise ValueError(
                "Tool-argument root cause requires observed tool-call arguments"
            )
        tool_name = trace.tool_calls[-1]
        contract = find_tool_contract(agent_config.tools, tool_name)
        if contract is None:
            raise ValueError(
                f"No registered tool contract for selected tool {tool_name!r}"
            )
        observed = trace.tool_call_arguments[-1]
        validation = validate_tool_arguments(contract, observed)
        if validation.valid:
            raise ValueError(
                "Tool-argument failure lacks a contract violation in trace evidence"
            )
        properties, required = argument_contract_parts(contract)
        observed_keys = sorted(observed)
        required_keys = sorted(required)
        evidence.extend(
            [
                f"selected tool: {tool_name}",
                f"observed argument keys: {observed_keys}",
                f"required argument keys: {required_keys}",
                f"missing required arguments: {validation.missing_required_arguments}",
                f"unexpected arguments: {validation.unexpected_arguments}",
            ]
        )
        observations.append(
            {
                "tool_name": tool_name,
                "observed_arguments": dict(observed),
                "argument_schema": {"properties": properties, "required": required},
                "missing_required_arguments": validation.missing_required_arguments,
                "unexpected_arguments": validation.unexpected_arguments,
            }
        )
    first = observations[0]
    return RootCauseAnalysis(
        failure_category=failure_pattern.category,
        evidence=evidence,
        root_cause=(
            "The selected tool's observed arguments do not satisfy its registered "
            "argument contract."
        ),
        target_component="tool_description",
        confidence=0.99,
        metadata=first,
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
