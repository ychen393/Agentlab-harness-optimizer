"""Evidence-driven adaptive challenges for the Commerce target testbed."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.runner import TargetAgent, run_benchmark
from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    FailurePattern,
    RootCauseAnalysis,
    TestCase,
)

from .domain_models import (
    CommerceGroundTruth,
    CommerceScenario,
    EligibilityRequest,
)
from .evaluator import evaluate_commerce
from .tools import check_eligibility, search_policy


@dataclass(frozen=True)
class _ChallengeSpec:
    family: str
    purchase_date: date
    purchase_amount: int | None


_CHALLENGE_SPECS = (
    _ChallengeSpec("policy_start_exact_threshold", date(2026, 1, 1), 500),
    _ChallengeSpec("policy_end_below_threshold", date(2026, 1, 31), 499),
    _ChallengeSpec("policy_start_exact_threshold", date(2026, 2, 1), 600),
    _ChallengeSpec("policy_end_below_threshold", date(2026, 2, 28), 599),
    _ChallengeSpec("missing_purchase_amount", date(2026, 2, 10), None),
)
_FAMILY_BY_SCENARIO_ID = {
    f"AC{index}": spec.family
    for index, spec in enumerate(_CHALLENGE_SPECS, start=1)
}


def generate_challenges(
    failure_patterns: list[FailurePattern],
    root_cause_analyses: list[RootCauseAnalysis],
    existing_scenarios: Sequence[CommerceScenario],
    num_challenges: int = 5,
) -> list[CommerceScenario]:
    """Generate distinct deterministic challenges from supported failure evidence."""

    _validate_adaptation_evidence(failure_patterns, root_cause_analyses)
    if num_challenges <= 0:
        raise ValueError("num_challenges must be greater than 0")
    if num_challenges > len(_CHALLENGE_SPECS):
        raise ValueError(
            f"Only {len(_CHALLENGE_SPECS)} deterministic Commerce challenges "
            "are supported in this phase"
        )

    existing_inputs = {
        _normalize_input(scenario.test_case.input) for scenario in existing_scenarios
    }
    existing_signatures = {
        _scenario_signature(scenario.test_case.input)
        for scenario in existing_scenarios
    }
    existing_ids = {scenario.id for scenario in existing_scenarios}
    existing_test_ids = {scenario.test_case.id for scenario in existing_scenarios}
    generated: list[CommerceScenario] = []

    for index, spec in enumerate(_CHALLENGE_SPECS, start=1):
        scenario = _build_challenge(index, spec)
        normalized_input = _normalize_input(scenario.test_case.input)
        signature = _scenario_signature(scenario.test_case.input)
        if (
            scenario.id in existing_ids
            or scenario.test_case.id in existing_test_ids
            or normalized_input in existing_inputs
            or signature in existing_signatures
        ):
            continue
        generated.append(scenario)
        existing_inputs.add(normalized_input)
        existing_signatures.add(signature)
        if len(generated) == num_challenges:
            return generated

    raise ValueError(
        f"Could not generate {num_challenges} distinct Commerce challenges "
        "without duplicating the existing scenario set"
    )


def challenge_family(scenario: CommerceScenario) -> str:
    """Return the stable family label for a generated adaptive challenge."""

    try:
        return _FAMILY_BY_SCENARIO_ID[scenario.id]
    except KeyError as error:
        raise ValueError(f"Unknown adaptive challenge ID: {scenario.id!r}") from error


def run_challenges(
    challenges: Sequence[CommerceScenario],
    target_agent: TargetAgent,
    agent_config: AgentConfig,
) -> tuple[list[ExecutionTrace], list[EvaluationResult]]:
    """Run and independently evaluate a separate Commerce challenge set."""

    challenge_items = tuple(challenges)
    if not challenge_items:
        raise ValueError("challenges must contain at least one CommerceScenario")
    traces = run_benchmark(
        [scenario.test_case for scenario in challenge_items],
        agent_config,
        target_agent,
    )
    evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(challenge_items, traces, strict=True)
    ]
    return traces, evaluations


def _validate_adaptation_evidence(
    failure_patterns: list[FailurePattern],
    root_cause_analyses: list[RootCauseAnalysis],
) -> None:
    if not any(
        pattern.category == "workflow_step_limit" for pattern in failure_patterns
    ):
        raise ValueError(
            "No supported workflow_step_limit FailurePattern was supplied"
        )
    if not any(
        analysis.failure_category == "workflow_step_limit"
        and analysis.target_component == "workflow_config"
        and any("max_steps" in evidence for evidence in analysis.evidence)
        for analysis in root_cause_analyses
    ):
        raise ValueError(
            "No evidence-backed workflow_config RootCauseAnalysis was supplied"
        )


def _build_challenge(index: int, spec: _ChallengeSpec) -> CommerceScenario:
    scenario_id = f"AC{index}"
    test_id = f"AT{index}"
    if spec.purchase_amount is None:
        user_input = (
            f"My order was paid on {spec.purchase_date.isoformat()}. "
            "Which promotion applies, and do I qualify for the gift?"
        )
        ground_truth = CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_tool_calls=("search_policy", "check_eligibility"),
            expected_error=True,
        )
        category = "missing_context"
        difficulty = "hard"
    else:
        policies = search_policy(active_on=spec.purchase_date)
        if len(policies) != 1:
            raise ValueError(
                "Canonical policy fixtures must identify exactly one policy for "
                f"{spec.purchase_date.isoformat()}"
            )
        policy = policies[0]
        expected = check_eligibility(
            EligibilityRequest(
                policy_id=policy.id,
                purchase_amount=spec.purchase_amount,
                purchase_date=spec.purchase_date,
            )
        )
        user_input = (
            f"My order was paid on {spec.purchase_date.isoformat()} for "
            f"{spec.purchase_amount} RMB. Which promotion applies, and do I "
            "qualify for the gift?"
        )
        ground_truth = CommerceGroundTruth(
            expected_tool="check_eligibility",
            expected_tool_calls=("search_policy", "check_eligibility"),
            expected_policy_id=expected.policy_id,
            expected_eligible=expected.eligible,
            expected_gift=expected.gift,
        )
        category = "boundary"
        difficulty = "hard"

    return CommerceScenario(
        id=scenario_id,
        test_case=TestCase(
            id=test_id,
            input=user_input,
            category=category,
            difficulty=difficulty,
            requirement_ids=["R_ELIGIBILITY", "R_POLICY_DISCOVERY"],
        ),
        ground_truth=ground_truth,
    )


def _normalize_input(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _scenario_signature(value: str) -> tuple[str | None, int | None, bool]:
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    amount_match = re.search(
        r"(?:amount|spend|paid|for)\s*(?:is|of|:)?\s*(\d+)",
        value.casefold(),
    )
    policy_match = re.search(r"policy_[a-z]", value, re.IGNORECASE)
    return (
        date_match.group(0) if date_match else None,
        int(amount_match.group(1)) if amount_match else None,
        policy_match is not None,
    )
