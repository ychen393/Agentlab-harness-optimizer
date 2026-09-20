"""Tests for coverage-driven Commerce challenge discovery."""

import json

from app.optimizer import run_optimization_cycle
from app.schemas import AgentConfig, ToolConfig, WorkflowConfig
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    analyze_coverage,
    commerce_v1_config,
    evaluate_commerce,
    exploratory_family,
    generate_challenges,
    run_challenges,
)


class HarnessAwareMockLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if all(
            marker in prompt
            for marker in (
                "Prefer explicit product intent",
                "CUSTOM PRODUCT DESCRIPTION",
                "Negative promotion wording still indicates product lookup",
            )
        ):
            return json.dumps(
                {"tool": "search_products", "arguments": {"query": "Running Shoes"}}
            )
        return json.dumps({"tool": "search_policy", "arguments": {}})


def accepted_cycle():
    result = run_optimization_cycle(
        COMMERCE_SCENARIOS,
        commerce_v1_config(),
        CommerceAgent(),
        evaluate_commerce,
        candidate_version="commerce-v2",
    )
    assert result.regression_decision is not None
    assert result.regression_decision.decision == "accept"
    assert result.candidate_config is not None
    return result


def coverage_report():
    cycle = accepted_cycle()
    adaptive = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )
    return cycle, adaptive, analyze_coverage(COMMERCE_SCENARIOS, adaptive)


def test_coverage_report_uses_undercovered_dimensions_for_selection() -> None:
    _, _, report = coverage_report()

    assert {
        "policy_discovery",
        "eligibility_calculation",
        "policy_boundary_handling",
        "missing_purchase_amount",
        "insufficient_context",
    } <= set(report.covered_dimensions)
    assert {
        "missing_purchase_date",
        "tool_selection_ambiguity",
        "product_promotion_ambiguity",
        "conflicting_user_wording",
    } <= set(report.undercovered_dimensions)
    assert report.selected_challenge_families == [
        "missing_purchase_date",
        "product_promotion_ambiguity",
        "tool_selection_ambiguity",
        "conflicting_policy_instruction",
    ]


def test_exploratory_ids_are_stable_and_sets_remain_immutable() -> None:
    cycle = accepted_cycle()
    adaptive = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )
    regression_snapshot = [item.model_copy(deep=True) for item in COMMERCE_SCENARIOS]
    adaptive_snapshot = [item.model_copy(deep=True) for item in adaptive]

    first = analyze_coverage(COMMERCE_SCENARIOS, adaptive)
    second = analyze_coverage(COMMERCE_SCENARIOS, adaptive)

    assert first == second
    assert [item.id for item in first.generated_challenges] == [
        "EX1",
        "EX2",
        "EX3",
        "EX4",
    ]
    assert [item.test_case.id for item in first.generated_challenges] == [
        "EXT1",
        "EXT2",
        "EXT3",
        "EXT4",
    ]
    assert list(COMMERCE_SCENARIOS) == regression_snapshot
    assert adaptive == adaptive_snapshot


def test_exploratory_challenges_are_distinct_and_hide_expected_answers() -> None:
    _, adaptive, report = coverage_report()
    all_existing = [*COMMERCE_SCENARIOS, *adaptive]
    existing_inputs = {item.test_case.input.casefold() for item in all_existing}
    existing_ids = {item.id for item in all_existing}
    existing_test_ids = {item.test_case.id for item in all_existing}

    for scenario in report.generated_challenges:
        assert scenario.id not in existing_ids
        assert scenario.test_case.id not in existing_test_ids
        assert scenario.test_case.input.casefold() not in existing_inputs
        exposed = scenario.test_case.model_dump()
        assert "expected_policy_id" not in exposed
        assert "expected_eligible" not in exposed
        assert "expected_gift" not in exposed


def test_exploratory_ground_truth_is_deterministic() -> None:
    _, _, first = coverage_report()
    _, _, second = coverage_report()

    assert [item.ground_truth for item in first.generated_challenges] == [
        item.ground_truth for item in second.generated_challenges
    ]
    assert first.generated_challenges[0].ground_truth.expected_error is True
    assert first.generated_challenges[1].ground_truth.expected_tool == "search_products"
    assert first.generated_challenges[2].ground_truth.expected_tool == "search_policy"
    assert first.generated_challenges[3].ground_truth.expected_eligible is False


def test_v2_executes_exploration_without_patch_or_v3(monkeypatch) -> None:
    cycle, _, report = coverage_report()
    config_snapshot = cycle.candidate_config.model_copy(deep=True)
    scenario_snapshot = [item.model_copy(deep=True) for item in report.generated_challenges]
    evaluator_calls: list[str] = []

    def tracked_evaluator(scenario, trace):
        evaluator_calls.append(scenario.id)
        return evaluate_commerce(scenario, trace)

    def unexpected_patch(*args, **kwargs):
        raise AssertionError("Phase 12 must not generate a HarnessPatch")

    monkeypatch.setattr(
        "app.targets.commerce.challenges.evaluate_commerce", tracked_evaluator
    )
    monkeypatch.setattr("app.optimizer.propose_harness_patch", unexpected_patch)

    traces, evaluations = run_challenges(
        report.generated_challenges,
        CommerceAgent(),
        cycle.candidate_config,
    )

    assert [trace.test_id for trace in traces] == [
        item.test_case.id for item in report.generated_challenges
    ]
    assert all(trace.agent_version == "commerce-v2" for trace in traces)
    assert all(evaluation.agent_version == "commerce-v2" for evaluation in evaluations)
    assert cycle.candidate_config == config_snapshot
    assert report.generated_challenges == scenario_snapshot
    assert not any(trace.agent_version == "commerce-v3" for trace in traces)
    assert evaluator_calls == [item.id for item in report.generated_challenges]
    assert evaluations == [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(report.generated_challenges, traces, strict=True)
    ]


def test_llm_routing_path_is_genuinely_influenced_by_editable_harness_fields() -> None:
    _, _, report = coverage_report()
    ambiguous = report.generated_challenges[1]
    llm = HarnessAwareMockLLM()
    config = AgentConfig(
        version="commerce-exploration",
        system_prompt="Prefer explicit product intent over negated promotion wording.",
        tools=[
            ToolConfig(
                name="search_products",
                description="CUSTOM PRODUCT DESCRIPTION",
            )
        ],
        context=["Negative promotion wording still indicates product lookup."],
        workflow=WorkflowConfig(max_steps=3),
    )

    trace = CommerceAgent(llm=llm).run(ambiguous.test_case, config)
    evaluation = evaluate_commerce(ambiguous, trace)

    assert trace.tool_calls == ["search_products"]
    assert evaluation.passed is True
    assert config.system_prompt in llm.prompts[0]
    assert config.tools[0].description in llm.prompts[0]
    assert config.context[0] in llm.prompts[0]


def test_exploratory_families_are_explicit() -> None:
    _, _, report = coverage_report()

    assert [exploratory_family(item) for item in report.generated_challenges] == [
        "missing_purchase_date",
        "product_promotion_ambiguity",
        "tool_selection_ambiguity",
        "conflicting_policy_instruction",
    ]
