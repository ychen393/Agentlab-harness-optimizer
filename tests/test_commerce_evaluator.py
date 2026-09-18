"""Tests for independent deterministic Commerce evaluation."""

import json
from inspect import signature

import pytest
from pydantic import ValidationError

from app.runner import run_agent
from app.schemas import AgentConfig, EvaluationResult, ExecutionTrace, WorkflowConfig
from app.targets.commerce import COMMERCE_SCENARIOS, CommerceAgent, evaluate_commerce


def trace(
    *,
    policy_id: str = "POLICY_A",
    eligible: bool = True,
    gift: str | None = "Gift A",
    tool_calls: list[str] | None = None,
    error: str | None = None,
) -> ExecutionTrace:
    output = "" if error else json.dumps(
        {
            "tool": "check_eligibility",
            "result": {
                "policy_id": policy_id,
                "eligible": eligible,
                "gift": gift,
                "reason": "eligible" if eligible else "insufficient_purchase_amount",
            },
        }
    )
    return ExecutionTrace(
        test_id="CT1",
        agent_version="commerce-v1",
        output=output,
        tool_calls=(
            ["check_eligibility"] if tool_calls is None else tool_calls
        ),
        error=error,
    )


def test_known_correct_execution_passes() -> None:
    evaluation = evaluate_commerce(COMMERCE_SCENARIOS[0], trace())

    assert isinstance(evaluation, EvaluationResult)
    assert evaluation.passed is True
    assert evaluation.final_score == 1.0
    assert all(score == 1.0 for score in evaluation.rule_scores.values())


def test_wrong_policy_fails() -> None:
    evaluation = evaluate_commerce(
        COMMERCE_SCENARIOS[0], trace(policy_id="POLICY_B")
    )

    assert evaluation.passed is False
    assert evaluation.rule_scores["correct_policy"] == 0.0


def test_wrong_eligibility_fails() -> None:
    evaluation = evaluate_commerce(
        COMMERCE_SCENARIOS[0], trace(eligible=False, gift=None)
    )

    assert evaluation.passed is False
    assert evaluation.rule_scores["correct_eligibility"] == 0.0


def test_missing_required_tool_fails() -> None:
    evaluation = evaluate_commerce(
        COMMERCE_SCENARIOS[0], trace(tool_calls=[])
    )

    assert evaluation.passed is False
    assert evaluation.rule_scores["required_tool_called"] == 0.0


def test_execution_error_fails() -> None:
    evaluation = evaluate_commerce(
        COMMERCE_SCENARIOS[0], trace(error="execution failed")
    )

    assert evaluation.passed is False
    assert evaluation.rule_scores["execution_succeeded"] == 0.0


def test_expected_missing_information_error_passes() -> None:
    scenario = COMMERCE_SCENARIOS[4]
    execution = ExecutionTrace(
        test_id=scenario.test_case.id,
        agent_version="commerce-v1",
        output=json.dumps({"error": "missing purchase details"}),
        tool_calls=["check_eligibility"],
        error="missing purchase details",
    )

    evaluation = evaluate_commerce(scenario, execution)

    assert evaluation.passed is True
    assert evaluation.rule_scores["execution_succeeded"] == 1.0
    assert evaluation.rule_scores["missing_information_detected"] == 1.0


def test_unexpected_execution_error_fails_expected_error_scenario() -> None:
    scenario = COMMERCE_SCENARIOS[4]
    execution = ExecutionTrace(
        test_id=scenario.test_case.id,
        agent_version="commerce-v1",
        output=json.dumps({"error": "network crashed"}),
        tool_calls=["check_eligibility"],
        error="network crashed",
    )

    evaluation = evaluate_commerce(scenario, execution)

    assert evaluation.passed is False
    assert evaluation.rule_scores["execution_succeeded"] == 0.0
    assert evaluation.rule_scores["missing_information_detected"] == 0.0


def test_expected_error_fails_when_agent_proceeds_as_if_input_is_complete() -> None:
    scenario = COMMERCE_SCENARIOS[4]

    evaluation = evaluate_commerce(scenario, trace())

    assert evaluation.passed is False
    assert evaluation.rule_scores["execution_succeeded"] == 0.0
    assert evaluation.rule_scores["missing_information_detected"] == 0.0


def test_evaluator_uses_ground_truth_without_mutating_it() -> None:
    scenario = COMMERCE_SCENARIOS[0]
    snapshot = scenario.model_copy(deep=True)

    evaluation = evaluate_commerce(scenario, trace(policy_id="POLICY_B"))

    assert evaluation.rule_scores["correct_policy"] == 0.0
    assert scenario == snapshot
    with pytest.raises(ValidationError):
        scenario.ground_truth.expected_policy_id = "POLICY_B"


def test_evaluator_does_not_invoke_target_agent() -> None:
    evaluation = evaluate_commerce(COMMERCE_SCENARIOS[0], trace())

    assert list(signature(evaluate_commerce).parameters) == ["scenario", "trace"]
    assert evaluation.passed is True


def test_target_agent_receives_no_hidden_expected_answers() -> None:
    class InspectingTargetAgent:
        def __init__(self) -> None:
            self.received_fields: set[str] = set()

        def run(self, test_case, agent_config):
            self.received_fields = set(test_case.model_dump())
            return trace()

    target = InspectingTargetAgent()
    scenario = COMMERCE_SCENARIOS[0]
    config = AgentConfig(
        version="commerce-v1",
        system_prompt="Route commerce requests.",
        tools=[],
        context=[],
        workflow=WorkflowConfig(),
    )

    run_agent(scenario.test_case, config, target)

    assert target.received_fields == {
        "id",
        "input",
        "category",
        "difficulty",
        "requirement_ids",
    }
    assert not {
        "expected_policy_id",
        "expected_eligible",
        "expected_gift",
    } & target.received_fields


def test_policy_discovery_scenario_does_not_expose_expected_policy_id() -> None:
    scenario = COMMERCE_SCENARIOS[5]

    assert "POLICY_B" not in scenario.test_case.input
    assert "expected_policy_id" not in scenario.test_case.model_dump()


def test_policy_discovery_tool_sequence_is_evaluated() -> None:
    scenario = COMMERCE_SCENARIOS[5]
    config = AgentConfig(
        version="commerce-v1",
        system_prompt="Discover policy before checking eligibility.",
        tools=[],
        context=[],
        workflow=WorkflowConfig(max_steps=3),
    )

    execution = run_agent(scenario.test_case, config, CommerceAgent())
    evaluation = evaluate_commerce(scenario, execution)

    assert execution.tool_calls == ["search_policy", "check_eligibility"]
    assert evaluation.passed is True
    assert evaluation.rule_scores["correct_tool_sequence"] == 1.0


def test_evaluation_preserves_trace_identity() -> None:
    execution = trace()
    evaluation = evaluate_commerce(COMMERCE_SCENARIOS[0], execution)

    assert evaluation.test_id == "CT1"
    assert evaluation.agent_version == "commerce-v1"


def test_end_to_end_scenario_runner_agent_evaluator() -> None:
    scenario = COMMERCE_SCENARIOS[3]
    config = AgentConfig(
        version="commerce-v1",
        system_prompt="Route commerce requests.",
        tools=[],
        context=[],
        workflow=WorkflowConfig(),
    )

    execution = run_agent(scenario.test_case, config, CommerceAgent())
    evaluation = evaluate_commerce(scenario, execution)

    assert execution.error is None
    assert evaluation.passed is True
    assert evaluation.final_score == 1.0
    assert evaluation.semantic_scores == {}
