"""Generic instruction-constraint detection and bounded prompt repair tests."""

from app.debugger import analyze_failures, analyze_root_cause
from app.optimizer import SystemPromptConstraintPatchStrategy
from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    InstructionConstraint,
    WorkflowConfig,
)


def support_config() -> AgentConfig:
    return AgentConfig(
        version="support-v1",
        system_prompt="Answer support questions clearly.",
        tools=[],
        instruction_constraints=[
            InstructionConstraint(
                id="support-no-cancellation",
                condition="the user requests information only and rejects cancellation",
                required_behavior="provide account information",
                forbidden_behavior="invoke cancellation",
                required_behavior_key="account_information",
                forbidden_behavior_key="cancel_subscription",
                instruction_lead="Respect explicit user constraints",
            )
        ],
        workflow=WorkflowConfig(max_steps=2),
    )


def support_trace() -> ExecutionTrace:
    return ExecutionTrace(
        test_id="SUPPORT-1",
        agent_version="support-v1",
        output="cancelled",
        tool_calls=["cancel_subscription"],
    )


def support_evaluation() -> EvaluationResult:
    return EvaluationResult(
        test_id="SUPPORT-1",
        agent_version="support-v1",
        passed=False,
        final_score=0.0,
        rule_scores={"required_tool_called": 0.0},
        semantic_scores={},
        failed_requirement_ids=["R_SUPPORT"],
        explanation="The required support behavior was not followed.",
    )


def test_instruction_constraint_contract_is_structured() -> None:
    constraint = support_config().instruction_constraints[0]

    assert constraint.id == "support-no-cancellation"
    assert constraint.required_behavior == "provide account information"
    assert constraint.forbidden_behavior == "invoke cancellation"


def test_generic_constraint_violation_is_classified() -> None:
    config = support_config()
    patterns = analyze_failures(
        [support_evaluation()], [support_trace()], config
    )

    assert patterns[0].category == "tool_usage_failure"


def test_generic_constraint_root_cause_is_structured() -> None:
    config = support_config()
    trace = support_trace()
    pattern = analyze_failures([support_evaluation()], [trace], config)[0]

    root_cause = analyze_root_cause(pattern, [trace], config)

    assert root_cause.target_component == "system_prompt"
    assert root_cause.metadata["constraint_id"] == "support-no-cancellation"
    assert root_cause.metadata["observed_behavior"] == "invoke cancellation"
    assert "Commerce" not in root_cause.root_cause


def test_generic_system_prompt_patch_preserves_prompt_and_constraint_semantics() -> None:
    config = support_config()
    trace = support_trace()
    pattern = analyze_failures([support_evaluation()], [trace], config)[0]
    root_cause = analyze_root_cause(pattern, [trace], config)

    patch = SystemPromptConstraintPatchStrategy().propose(
        pattern, root_cause, config
    )

    assert patch is not None
    assert patch.target_component == "system_prompt"
    candidate = patch.proposed_value["system_prompt"]
    assert candidate.startswith(config.system_prompt)
    assert "information only" in candidate
    assert "provide account information" in candidate
    assert "invoke cancellation" in candidate
    assert "SUPPORT-1" not in candidate
    assert "Commerce" not in candidate


def test_system_prompt_patch_is_unavailable_without_registered_constraint() -> None:
    config = support_config().model_copy(update={"instruction_constraints": []})
    trace = support_trace()
    pattern = analyze_failures(
        [support_evaluation()], [trace], support_config()
    )[0]
    root_cause = analyze_root_cause(pattern, [trace], support_config())

    assert SystemPromptConstraintPatchStrategy().propose(
        pattern, root_cause, config
    ) is None


def test_system_prompt_patch_is_unavailable_for_non_prompt_target() -> None:
    config = support_config()
    trace = support_trace()
    pattern = analyze_failures([support_evaluation()], [trace], config)[0]
    root_cause = analyze_root_cause(
        pattern, [trace], config
    ).model_copy(update={"target_component": "context"})

    assert SystemPromptConstraintPatchStrategy().propose(
        pattern, root_cause, config
    ) is None


def test_equivalent_instruction_is_not_appended_twice() -> None:
    config = support_config()
    trace = support_trace()
    pattern = analyze_failures([support_evaluation()], [trace], config)[0]
    root_cause = analyze_root_cause(pattern, [trace], config)
    first = SystemPromptConstraintPatchStrategy().propose(
        pattern, root_cause, config
    )
    assert first is not None
    complete = config.model_copy(
        update={"system_prompt": first.proposed_value["system_prompt"]}
    )

    assert SystemPromptConstraintPatchStrategy().propose(
        pattern, root_cause, complete
    ) is None
