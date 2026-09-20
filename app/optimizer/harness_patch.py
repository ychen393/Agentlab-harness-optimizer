"""Deterministic bounded patch proposals for supported root causes."""

import re

from app.schemas import AgentConfig, FailurePattern, HarnessPatch, RootCauseAnalysis


_WORKFLOW_STEP_PATTERN = re.compile(r"workflow step\s+(\d+)", re.IGNORECASE)


def propose_harness_patch(
    failure_pattern: FailurePattern,
    root_cause: RootCauseAnalysis,
    current_config: AgentConfig,
) -> HarnessPatch:
    """Propose one evidence-backed patch for a supported root cause."""

    if failure_pattern.category != root_cause.failure_category:
        raise ValueError(
            "FailurePattern category does not match RootCauseAnalysis category"
        )
    if (
        failure_pattern.category == "tool_usage_failure"
        and root_cause.target_component == "system_prompt"
    ):
        return _system_prompt_patch(failure_pattern, root_cause, current_config)
    if root_cause.target_component != "workflow_config":
        raise ValueError(
            "Unsupported target component for deterministic patch proposal: "
            f"{root_cause.target_component!r}"
        )
    if failure_pattern.category != "workflow_step_limit":
        raise ValueError(
            "Unsupported failure category for deterministic patch proposal: "
            f"{failure_pattern.category!r}"
        )

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
            "Expected to allow the observed search_policy to check_eligibility "
            "multi-step workflow to complete."
        ),
        regression_risk=(
            "Allowing an additional workflow step may increase latency or cost "
            "and could permit unnecessary extra tool usage."
        ),
    )


def _system_prompt_patch(
    failure_pattern: FailurePattern,
    root_cause: RootCauseAnalysis,
    current_config: AgentConfig,
) -> HarnessPatch:
    prompt_evidence = f"Current system_prompt is {current_config.system_prompt!r}."
    if prompt_evidence not in root_cause.evidence:
        raise ValueError(
            "RootCauseAnalysis lacks concrete current system_prompt evidence"
        )
    instruction = (
        "Honor explicit exclusions and negated intent: promotion-related words "
        "alone must not trigger policy lookup when the user explicitly requests "
        "product lookup and excludes promotion lookup."
    )
    proposed_prompt = f"{current_config.system_prompt.rstrip()}\n\n{instruction}"
    return HarnessPatch(
        target_component="system_prompt",
        old_value={"system_prompt": current_config.system_prompt},
        proposed_value={"system_prompt": proposed_prompt},
        reason=(
            f"FailurePattern {failure_pattern.id} records completed execution "
            "with incorrect required-tool usage, and the root-cause evidence "
            "shows the current prompt lacks explicit negated-intent guidance."
        ),
        supporting_failure_pattern_ids=[failure_pattern.id],
        expected_effect=(
            "Expected to prefer the user's explicit product-lookup intent over "
            "promotion keywords appearing in an excluded context."
        ),
        regression_risk=(
            "Stronger exclusion handling could under-select policy lookup for "
            "poorly phrased requests, so fixed and held-out suites must be rerun."
        ),
    )


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
