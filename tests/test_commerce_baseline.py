"""End-to-end evidence for the intentionally constrained Commerce V1 harness."""

import json

from app.runner import run_agent
from app.schemas import WorkflowConfig
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    commerce_v1_config,
    evaluate_commerce,
)


def test_commerce_v1_config_is_reusable_and_step_limited() -> None:
    first = commerce_v1_config()
    second = commerce_v1_config()

    assert first.version == "commerce-v1"
    assert first.workflow.max_steps == 2
    assert first is not second
    assert first.workflow is not second.workflow


def test_commerce_v1_baseline_produces_recurring_workflow_failures() -> None:
    config = commerce_v1_config()
    agent = CommerceAgent()
    results = []

    for scenario in COMMERCE_SCENARIOS:
        trace = run_agent(scenario.test_case, config, agent)
        evaluation = evaluate_commerce(scenario, trace)
        failed_checks = [
            metric
            for metric, score in evaluation.rule_scores.items()
            if score < 1.0
        ]
        results.append((scenario.id, trace, evaluation, failed_checks))

    simple_results = results[:5]
    discovery_results = results[5:]

    assert all(evaluation.passed for _, _, evaluation, _ in simple_results)
    assert [scenario_id for scenario_id, _, _, _ in discovery_results] == [
        "CS6",
        "CS7",
    ]
    assert all(
        trace.tool_calls == ["search_policy"]
        for _, trace, _, _ in discovery_results
    )
    assert all(
        trace.error is not None and "max_steps=2" in trace.error
        for _, trace, _, _ in discovery_results
    )
    assert all(not evaluation.passed for _, _, evaluation, _ in discovery_results)
    assert all(
        "correct_tool_sequence" in failed_checks
        for _, _, _, failed_checks in discovery_results
    )


def test_non_qualifying_discovery_ground_truth_is_hidden_and_business_logic_works() -> None:
    scenario = COMMERCE_SCENARIOS[6]
    config = commerce_v1_config().model_copy(
        update={"workflow": WorkflowConfig(max_steps=3)}
    )

    trace = run_agent(scenario.test_case, config, CommerceAgent())
    evaluation = evaluate_commerce(scenario, trace)
    result = json.loads(trace.output)["result"]

    assert "POLICY_B" not in scenario.test_case.input
    assert "expected_policy_id" not in scenario.test_case.model_dump()
    assert trace.tool_calls == ["search_policy", "check_eligibility"]
    assert result["policy_id"] == "POLICY_B"
    assert result["eligible"] is False
    assert result["gift"] is None
    assert evaluation.passed is True
