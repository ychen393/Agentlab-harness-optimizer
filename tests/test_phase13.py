"""Phase 13 patchability gate and second bounded optimization experiment."""

import json
import re

from app.optimizer import run_optimization_cycle
from app.schemas import AgentConfig, ExecutionTrace
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    analyze_coverage,
    assess_deterministic_patchability,
    commerce_v1_config,
    evaluate_commerce,
    generate_challenges,
    run_harness_sensitive_cycle,
    validate_harness_candidate,
)


class ControlledCommerceRouter:
    """One routing mechanism whose behavior responds to harness instructions."""

    patch_marker = "Honor explicit exclusions and negated intent"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        user_input = prompt.rsplit("User input: ", 1)[1]
        lowered = user_input.casefold()

        if "running shoes" in lowered and "promotion" in lowered:
            if self.patch_marker in prompt:
                return self._response("search_products", {"query": "Running Shoes"})
            return self._response("search_policy", {"policy_id": "POLICY_A"})

        eligibility = any(
            term in lowered for term in ("eligible", "eligibility", "qualify", "gift")
        )
        policy_match = re.search(r"policy_[a-z]", user_input, re.IGNORECASE)
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", user_input)
        amount_match = re.search(
            r"(?:amount|spend|paid|for|total)\s*(?:is|of|:)?\s*(\d+)",
            lowered,
        )
        if eligibility:
            if policy_match is None and date_match is not None:
                return self._response(
                    "search_policy", {"active_on": date_match.group(0)}
                )
            arguments = {}
            if policy_match:
                arguments["policy_id"] = policy_match.group(0).upper()
            if date_match:
                arguments["purchase_date"] = date_match.group(0)
            if amount_match:
                arguments["purchase_amount"] = int(amount_match.group(1))
            return self._response("check_eligibility", arguments)

        if "policy" in lowered or "promotion" in lowered:
            arguments = {}
            if policy_match:
                arguments["policy_id"] = policy_match.group(0).upper()
            if date_match:
                arguments["active_on"] = date_match.group(0)
            return self._response("search_policy", arguments)
        return self._response("search_products", {"query": user_input})

    @staticmethod
    def _response(tool: str, arguments: dict) -> str:
        return json.dumps({"tool": tool, "arguments": arguments})


def phase13_inputs():
    first_cycle = run_optimization_cycle(
        COMMERCE_SCENARIOS,
        commerce_v1_config(),
        CommerceAgent(),
        evaluate_commerce,
        candidate_version="commerce-v2",
    )
    assert first_cycle.candidate_config is not None
    assert first_cycle.regression_decision is not None
    adaptive = generate_challenges(
        first_cycle.failure_patterns,
        first_cycle.root_cause_analyses,
        COMMERCE_SCENARIOS,
    )
    coverage = analyze_coverage(COMMERCE_SCENARIOS, adaptive)
    ex2 = next(item for item in coverage.generated_challenges if item.id == "EX2")
    return first_cycle.candidate_config, adaptive, coverage.generated_challenges, ex2


def test_deterministic_ex2_is_explicitly_not_patchable() -> None:
    v2, _, _, ex2 = phase13_inputs()

    result = assess_deterministic_patchability(ex2, v2)

    assert result.baseline_evaluations[0].passed is False
    assert result.baseline_traces[0].tool_calls == ["search_policy"]
    assert result.status == "patch_unavailable"
    assert "does not consume system_prompt, tool descriptions, or context" in result.message
    assert result.proposed_patch is None
    assert result.candidate_config is None
    assert result.regression_decision is None


def test_harness_sensitive_cycle_uses_real_failure_and_same_router() -> None:
    v2, _, _, ex2 = phase13_inputs()
    router = ControlledCommerceRouter()
    v2_snapshot = v2.model_copy(deep=True)
    ex2_snapshot = ex2.model_copy(deep=True)

    result = run_harness_sensitive_cycle(
        ex2, v2, router, candidate_version="commerce-v3"
    )

    assert result.status == "completed"
    assert result.baseline_traces[0].tool_calls == ["search_policy"]
    assert result.baseline_evaluations[0].passed is False
    assert result.failure_patterns[0].category == "tool_usage_failure"
    assert result.root_cause_analyses[0].target_component == "system_prompt"
    assert "search_policy" in " ".join(result.root_cause_analyses[0].evidence)
    assert result.proposed_patch is not None
    assert result.proposed_patch.target_component == "system_prompt"
    assert result.candidate_config is not None
    assert result.candidate_traces[0].tool_calls == ["search_products"]
    assert result.candidate_evaluations[0].passed is True
    assert len(router.prompts) == 2
    assert ControlledCommerceRouter.patch_marker not in router.prompts[0]
    assert ControlledCommerceRouter.patch_marker in router.prompts[1]
    assert v2 == v2_snapshot
    assert ex2 == ex2_snapshot

    baseline_values = result.baseline_config.model_dump(exclude={"version", "system_prompt"})
    candidate_values = result.candidate_config.model_dump(exclude={"version", "system_prompt"})
    assert baseline_values == candidate_values
    assert result.regression_decision is not None
    expected_decision = (
        "reject"
        if result.regression_decision.regressed_test_ids
        else "accept"
        if result.regression_decision.improved_test_ids
        else "review"
    )
    assert result.regression_decision.decision == expected_decision


def test_passing_llm_baseline_does_not_justify_v3() -> None:
    v2, _, _, ex2 = phase13_inputs()

    def passing_router(prompt: str) -> str:
        return json.dumps(
            {"tool": "search_products", "arguments": {"query": "Running Shoes"}}
        )

    result = run_harness_sensitive_cycle(
        ex2, v2, passing_router, candidate_version="commerce-v3"
    )

    assert result.status == "no_failures"
    assert result.proposed_patch is None
    assert result.candidate_config is None


def test_unsupported_execution_root_cause_produces_no_patch() -> None:
    v2, _, _, ex2 = phase13_inputs()

    def broken_router(prompt: str) -> str:
        return json.dumps({"tool": "search_policy", "arguments": {}})

    result = run_harness_sensitive_cycle(
        ex2, v2, broken_router, candidate_version="commerce-v3"
    )

    assert result.status == "patch_unavailable"
    assert result.failure_patterns[0].category == "execution_error"
    assert result.proposed_patch is None
    assert result.candidate_config is None


def test_v3_validation_reruns_ct_ac_and_ex_and_derives_decision() -> None:
    v2, adaptive, exploratory, ex2 = phase13_inputs()
    cycle = run_harness_sensitive_cycle(
        ex2, v2, ControlledCommerceRouter(), candidate_version="commerce-v3"
    )
    assert cycle.candidate_config is not None
    fixed_snapshot = [item.model_copy(deep=True) for item in COMMERCE_SCENARIOS]
    adaptive_snapshot = [item.model_copy(deep=True) for item in adaptive]
    exploratory_snapshot = [item.model_copy(deep=True) for item in exploratory]
    router = ControlledCommerceRouter()

    baseline_traces, baseline_results, candidate_traces, candidate_results, decision = (
        validate_harness_candidate(
            COMMERCE_SCENARIOS,
            adaptive,
            exploratory,
            v2,
            cycle.candidate_config,
            router,
        )
    )

    expected_ids = {
        item.test_case.id for item in [*COMMERCE_SCENARIOS, *adaptive, *exploratory]
    }
    assert {item.test_id for item in baseline_traces} == expected_ids
    assert {item.test_id for item in candidate_traces} == expected_ids
    assert {item.test_id for item in baseline_results} == expected_ids
    assert {item.test_id for item in candidate_results} == expected_ids
    assert len(router.prompts) == 2 * len(expected_ids)
    assert list(COMMERCE_SCENARIOS) == fixed_snapshot
    assert adaptive == adaptive_snapshot
    assert exploratory == exploratory_snapshot

    expected_decision = (
        "reject"
        if decision.regressed_test_ids
        else "accept"
        if decision.improved_test_ids
        else "review"
    )
    assert decision.decision == expected_decision
