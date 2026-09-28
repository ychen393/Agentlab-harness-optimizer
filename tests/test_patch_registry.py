"""Generic patch-strategy registry tests independent of any target agent."""

from app.optimizer import (
    PatchProposalRegistry,
    WorkflowStepLimitPatchStrategy,
)
from app.schemas import (
    AgentConfig,
    FailurePattern,
    HarnessPatch,
    RootCauseAnalysis,
    WorkflowConfig,
)


def _workflow_inputs() -> tuple[FailurePattern, RootCauseAnalysis, AgentConfig]:
    return (
        FailurePattern(
            id="F-GENERIC",
            category="workflow_step_limit",
            count=1,
            affected_test_ids=["T-GENERIC"],
            severity="medium",
            summary="A workflow step was blocked.",
        ),
        RootCauseAnalysis(
            failure_category="workflow_step_limit",
            evidence=["T-GENERIC blocked at required workflow step 4"],
            root_cause="The configured workflow budget is insufficient.",
            target_component="workflow_config",
            confidence=0.9,
        ),
        AgentConfig(
            version="v1",
            system_prompt="Execute the task.",
            tools=[],
            context=[],
            workflow=WorkflowConfig(max_steps=3),
        ),
    )


def test_generic_workflow_strategy_derives_step_four_from_evidence() -> None:
    pattern, root_cause, config = _workflow_inputs()

    patch = WorkflowStepLimitPatchStrategy().propose(
        pattern, root_cause, config
    )

    assert patch is not None
    assert patch.target_component == "workflow_config"
    assert patch.old_value == {"max_steps": 3}
    assert patch.proposed_value == {"max_steps": 4}
    assert "search_policy" not in patch.expected_effect
    assert "check_eligibility" not in patch.expected_effect


class AlwaysSupportsStrategy:
    def supports(self, failure_pattern, root_cause, current_config) -> bool:
        return True

    def propose(self, failure_pattern, root_cause, current_config):
        return HarnessPatch(
            target_component="context",
            old_value={"context": []},
            proposed_value={"context": ["bounded"]},
            reason="Generic test strategy",
            supporting_failure_pattern_ids=[failure_pattern.id],
            expected_effect="Test effect",
            regression_risk="Test risk",
        )


def test_registry_selects_the_first_compatible_strategy() -> None:
    pattern, root_cause, config = _workflow_inputs()
    patch = PatchProposalRegistry(
        [AlwaysSupportsStrategy(), WorkflowStepLimitPatchStrategy()]
    ).propose(pattern, root_cause, config)

    assert patch is not None
    assert patch.target_component == "context"


def test_registry_returns_no_patch_when_no_strategy_supports() -> None:
    pattern, root_cause, config = _workflow_inputs()
    unsupported = root_cause.model_copy(
        update={
            "failure_category": "unknown_failure",
            "target_component": "context",
        }
    )

    assert (
        PatchProposalRegistry([WorkflowStepLimitPatchStrategy()]).propose(
            pattern, unsupported, config
        )
        is None
    )
