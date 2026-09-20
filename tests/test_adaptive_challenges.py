"""Tests for evidence-driven deterministic Commerce challenge generation."""

from datetime import date

import pytest

from app.optimizer import run_optimization_cycle
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    challenge_family,
    commerce_v1_config,
    evaluate_commerce,
    generate_challenges,
    run_challenges,
)
from app.targets.commerce.domain_models import EligibilityRequest
from app.targets.commerce.tools import check_eligibility, search_policy


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


def test_challenges_are_stable_distinct_and_evidence_driven() -> None:
    cycle = accepted_cycle()
    scenario_snapshot = [
        scenario.model_copy(deep=True) for scenario in COMMERCE_SCENARIOS
    ]

    first = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )
    second = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )

    assert first == second
    assert [scenario.id for scenario in first] == ["AC1", "AC2", "AC3", "AC4", "AC5"]
    assert [scenario.test_case.id for scenario in first] == [
        "AT1",
        "AT2",
        "AT3",
        "AT4",
        "AT5",
    ]
    assert {scenario.id for scenario in first}.isdisjoint(
        scenario.id for scenario in COMMERCE_SCENARIOS
    )
    assert {scenario.test_case.id for scenario in first}.isdisjoint(
        scenario.test_case.id for scenario in COMMERCE_SCENARIOS
    )
    assert list(COMMERCE_SCENARIOS) == scenario_snapshot


def test_generated_ground_truth_comes_from_canonical_domain_logic() -> None:
    cycle = accepted_cycle()
    challenges = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )

    for scenario in challenges[:4]:
        input_text = scenario.test_case.input
        purchase_date = date.fromisoformat(input_text.split(" on ")[1][:10])
        purchase_amount = int(input_text.split(" for ")[1].split()[0])
        policy = search_policy(active_on=purchase_date)[0]
        expected = check_eligibility(
            EligibilityRequest(
                policy_id=policy.id,
                purchase_amount=purchase_amount,
                purchase_date=purchase_date,
            )
        )

        assert scenario.ground_truth.expected_policy_id == expected.policy_id
        assert scenario.ground_truth.expected_eligible == expected.eligible
        assert scenario.ground_truth.expected_gift == expected.gift

    assert challenges[4].ground_truth.expected_error is True
    assert challenges[4].ground_truth.expected_policy_id is None
    assert challenges[4].ground_truth.expected_eligible is None


def test_expected_answers_are_not_exposed_to_target_agent_input() -> None:
    cycle = accepted_cycle()
    challenges = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )

    for scenario in challenges:
        exposed = scenario.test_case.model_dump()
        assert "expected_policy_id" not in exposed
        assert "expected_eligible" not in exposed
        assert "expected_gift" not in exposed
        assert "POLICY_A" not in scenario.test_case.input
        assert "POLICY_B" not in scenario.test_case.input
        assert "Gift A" not in scenario.test_case.input
        assert "Gift B" not in scenario.test_case.input


def test_duplicate_challenges_are_not_regenerated() -> None:
    cycle = accepted_cycle()
    challenges = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )

    with pytest.raises(ValueError, match="without duplicating"):
        generate_challenges(
            cycle.failure_patterns,
            cycle.root_cause_analyses,
            [*COMMERCE_SCENARIOS, *challenges],
        )


def test_accepted_v2_runs_and_is_evaluated_on_separate_challenge_set() -> None:
    cycle = accepted_cycle()
    challenges = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )
    challenge_snapshot = [item.model_copy(deep=True) for item in challenges]
    config_snapshot = cycle.candidate_config.model_copy(deep=True)

    traces, evaluations = run_challenges(
        challenges, CommerceAgent(), cycle.candidate_config
    )

    assert len(traces) == len(challenges)
    assert len(evaluations) == len(challenges)
    assert all(trace.agent_version == "commerce-v2" for trace in traces)
    assert [trace.test_id for trace in traces] == [
        scenario.test_case.id for scenario in challenges
    ]
    assert [evaluation.test_id for evaluation in evaluations] == [
        scenario.test_case.id for scenario in challenges
    ]
    assert all(evaluation.agent_version == "commerce-v2" for evaluation in evaluations)
    assert cycle.candidate_config == config_snapshot
    assert challenges == challenge_snapshot
    assert cycle.proposed_patch is not None
    assert cycle.proposed_patch.supporting_failure_pattern_ids == ["F1"]


def test_challenge_families_are_explicit_and_stable() -> None:
    cycle = accepted_cycle()
    challenges = generate_challenges(
        cycle.failure_patterns,
        cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )

    assert [challenge_family(scenario) for scenario in challenges] == [
        "policy_start_exact_threshold",
        "policy_end_below_threshold",
        "policy_start_exact_threshold",
        "policy_end_below_threshold",
        "missing_purchase_amount",
    ]


def test_generation_requires_supported_failure_and_root_cause_evidence() -> None:
    cycle = accepted_cycle()

    with pytest.raises(ValueError, match="FailurePattern"):
        generate_challenges([], cycle.root_cause_analyses, COMMERCE_SCENARIOS)
    with pytest.raises(ValueError, match="RootCauseAnalysis"):
        generate_challenges(cycle.failure_patterns, [], COMMERCE_SCENARIOS)
