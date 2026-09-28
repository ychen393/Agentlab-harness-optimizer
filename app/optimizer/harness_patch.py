"""Generic bounded patch-proposal strategies and their explicit registry."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol

from app.debugger.tool_arguments import argument_contract_parts, find_tool_contract
from app.schemas import AgentConfig, FailurePattern, HarnessPatch, RootCauseAnalysis


class PatchProposalStrategy(Protocol):
    """Minimal contract for a bounded, target-compatible patch strategy."""

    def supports(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> bool:
        ...

    def propose(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> HarnessPatch | None:
        ...


class PatchProposalRegistry:
    """Explicit strategy registry; the first compatible strategy wins."""

    def __init__(self, strategies: Sequence[PatchProposalStrategy] = ()) -> None:
        self.strategies = tuple(strategies)

    def propose(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> HarnessPatch | None:
        for strategy in self.strategies:
            if strategy.supports(failure_pattern, root_cause, current_config):
                return strategy.propose(failure_pattern, root_cause, current_config)
        return None


_WORKFLOW_STEP_PATTERN = re.compile(r"workflow step\s+(\d+)", re.IGNORECASE)


class WorkflowStepLimitPatchStrategy:
    """Evidence-derived bounded repair for an insufficient workflow budget."""

    def supports(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> bool:
        return (
            failure_pattern.category == "workflow_step_limit"
            and root_cause.failure_category == failure_pattern.category
            and root_cause.target_component == "workflow_config"
        )

    def propose(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> HarnessPatch | None:
        if not self.supports(failure_pattern, root_cause, current_config):
            return None
        required_step = _required_workflow_step(root_cause)
        current_max_steps = current_config.workflow.max_steps
        if required_step <= current_max_steps:
            raise ValueError(
                "RootCauseAnalysis does not support increasing workflow.max_steps: "
                f"required step {required_step} is not above current value "
                f"{current_max_steps}"
            )
        return HarnessPatch(
            target_component="workflow_config",
            old_value={"max_steps": current_max_steps},
            proposed_value={"max_steps": required_step},
            reason=(
                f"FailurePattern {failure_pattern.id} identifies recurring workflow "
                f"step-limit failures, and its root-cause evidence shows execution "
                f"is blocked at workflow step {required_step}."
            ),
            supporting_failure_pattern_ids=[failure_pattern.id],
            expected_effect=(
                "Expected to allow the required workflow step blocked by the "
                "current step budget to execute."
            ),
            regression_risk=(
                "Allowing an additional workflow step may increase latency or cost "
                "and could permit unnecessary extra tool usage."
            ),
        )


class ToolArgumentSchemaPatchStrategy:
    """Evidence-derived bounded repair for a registered tool argument contract."""

    def supports(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> bool:
        tool_name = root_cause.metadata.get("tool_name")
        return (
            failure_pattern.category == "tool_argument_schema_failure"
            and root_cause.failure_category == failure_pattern.category
            and root_cause.target_component == "tool_description"
            and isinstance(tool_name, str)
            and find_tool_contract(current_config.tools, tool_name) is not None
        )

    def propose(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> HarnessPatch | None:
        if not self.supports(failure_pattern, root_cause, current_config):
            return None
        tool_name = root_cause.metadata["tool_name"]
        contract = find_tool_contract(current_config.tools, tool_name)
        if contract is None:
            return None
        old_description = contract.description
        schema_instruction = (
            f" Arguments: {_schema_example(contract.argument_schema)}."
        )
        proposed_description = old_description.rstrip() + schema_instruction
        return HarnessPatch(
            target_component="tool_description",
            old_value={"name": tool_name, "description": old_description},
            proposed_value={"name": tool_name, "description": proposed_description},
            reason=(
                f"FailurePattern {failure_pattern.id} shows observed arguments "
                f"violating the registered contract for {tool_name!r}."
            ),
            supporting_failure_pattern_ids=[failure_pattern.id],
            expected_effect=(
                "Expected to make the registered argument contract explicit while "
                "preserving the existing tool description."
            ),
            regression_risk=(
                "An explicit argument schema may reduce robustness for callers "
                "using undocumented aliases."
            ),
        )


class SystemPromptConstraintPatchStrategy:
    """Evidence-derived bounded repair from a registered instruction constraint."""

    def supports(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> bool:
        constraint = _constraint_for_root_cause(root_cause, current_config)
        return (
            failure_pattern.category == "tool_usage_failure"
            and root_cause.failure_category == failure_pattern.category
            and root_cause.target_component == "system_prompt"
            and constraint is not None
            and root_cause.metadata.get("observed_behavior")
            == constraint.forbidden_behavior
            and root_cause.metadata.get("observed_behavior_key")
            == (constraint.forbidden_behavior_key or constraint.forbidden_behavior)
        )

    def propose(
        self,
        failure_pattern: FailurePattern,
        root_cause: RootCauseAnalysis,
        current_config: AgentConfig,
    ) -> HarnessPatch | None:
        if not self.supports(failure_pattern, root_cause, current_config):
            return None
        constraint = _constraint_for_root_cause(root_cause, current_config)
        if constraint is None:
            return None
        instruction = _render_constraint(constraint)
        normalized_prompt = _normalize(current_config.system_prompt)
        if _normalize(instruction) in normalized_prompt:
            return None
        proposed_prompt = f"{current_config.system_prompt.rstrip()}\n\n{instruction}"
        return HarnessPatch(
            target_component="system_prompt",
            old_value={"system_prompt": current_config.system_prompt},
            proposed_value={"system_prompt": proposed_prompt},
            reason=(
                f"FailurePattern {failure_pattern.id} shows behavior violating "
                f"registered instruction constraint {constraint.id!r}."
            ),
            supporting_failure_pattern_ids=[failure_pattern.id],
            expected_effect=(
                "Expected to encode the observed instruction constraint without "
                "rewriting the existing system prompt."
            ),
            regression_risk=(
                "A stronger constraint may suppress behavior in ambiguous cases; "
                "the same and held-out benchmarks must be rerun."
            ),
        )


def propose_harness_patch(
    failure_pattern: FailurePattern,
    root_cause: RootCauseAnalysis,
    current_config: AgentConfig,
) -> HarnessPatch:
    """Backward-compatible entry point for the generic workflow strategy."""

    if failure_pattern.category != root_cause.failure_category:
        raise ValueError(
            "FailurePattern category does not match RootCauseAnalysis category"
        )
    if (
        failure_pattern.category == "workflow_step_limit"
        and root_cause.target_component != "workflow_config"
    ):
        raise ValueError(
            "Unsupported target component for deterministic patch proposal: "
            f"{root_cause.target_component!r}"
        )
    patch = PatchProposalRegistry(
        (
            WorkflowStepLimitPatchStrategy(),
            ToolArgumentSchemaPatchStrategy(),
            SystemPromptConstraintPatchStrategy(),
        )
    ).propose(
        failure_pattern, root_cause, current_config
    )
    if patch is None:
        raise ValueError(
            "No compatible generic patch proposal strategy for failure category "
            f"{failure_pattern.category!r}"
        )
    return patch


def _required_workflow_step(root_cause: RootCauseAnalysis) -> int:
    observed_steps = [
        int(match.group(1))
        for evidence in root_cause.evidence
        if (match := _WORKFLOW_STEP_PATTERN.search(evidence)) is not None
    ]
    if not observed_steps:
        raise ValueError(
            "RootCauseAnalysis lacks concrete blocked workflow-step evidence"
        )
    return max(observed_steps)


def _schema_example(argument_schema: dict[str, object]) -> str:
    from app.schemas import ToolConfig

    properties, required = argument_contract_parts(
        ToolConfig(name="_contract", description="", argument_schema=argument_schema)
    )
    names = required or sorted(properties)
    example = {
        name: f"<{properties[name].get('type', 'value')}>"
        for name in names
        if isinstance(properties.get(name), dict)
    }
    if not example:
        raise ValueError("Tool argument contract does not define argument properties")
    import json

    return json.dumps(example, separators=(",", ":"), sort_keys=True)


def _constraint_for_root_cause(
    root_cause: RootCauseAnalysis, current_config: AgentConfig
):
    constraint_id = root_cause.metadata.get("constraint_id")
    if not isinstance(constraint_id, str):
        return None
    return next(
        (
            constraint
            for constraint in current_config.instruction_constraints
            if constraint.id == constraint_id
        ),
        None,
    )


def _render_constraint(constraint) -> str:
    return (
        f"{constraint.instruction_lead}: When {constraint.condition}, "
        f"{constraint.required_behavior}. Do not {constraint.forbidden_behavior}."
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
