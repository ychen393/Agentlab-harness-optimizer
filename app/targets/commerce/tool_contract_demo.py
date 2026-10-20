"""Controlled evidence for a tool-description contract repair.

This module turns the existing generic tool-argument debugger and bounded
ToolArgumentSchemaPatchStrategy into a reproducible Commerce experiment.

Only TD1 is used to derive the patch. TD2-TD4 are held-out validation cases and
TD5 is a negative control that is already contract-compliant before the patch.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.debugger import analyze_failures, analyze_root_cause
from app.optimizer import apply_harness_patch, propose_harness_patch, run_optimization_cycle
from app.regression import compare_versions
from app.runner import run_agent, run_benchmark
from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    FailurePattern,
    HarnessPatch,
    RegressionDecision,
    RootCauseAnalysis,
    TestCase,
)

from .agent import CommerceAgent
from .config import commerce_v1_config
from .domain_models import CommerceGroundTruth, CommerceScenario
from .evaluator import evaluate_commerce
from .scenarios import COMMERCE_SCENARIOS


TOOL_CONTRACT_CASES: tuple[CommerceScenario, ...] = (
    CommerceScenario(
        id="TC_SEED",
        test_case=TestCase(
            id="TD1",
            input="Find Running Shoes.",
            category="tool_contract_seed",
            difficulty="medium",
            requirement_ids=["R_PRODUCT_LOOKUP", "R_TOOL_ARGUMENT_CONTRACT"],
        ),
        ground_truth=CommerceGroundTruth(expected_tool="search_products"),
    ),
    CommerceScenario(
        id="TC_HELDOUT_1",
        test_case=TestCase(
            id="TD2",
            input="Do you have a Travel Backpack?",
            category="tool_contract_heldout",
            difficulty="medium",
            requirement_ids=["R_PRODUCT_LOOKUP", "R_TOOL_ARGUMENT_CONTRACT"],
        ),
        ground_truth=CommerceGroundTruth(expected_tool="search_products"),
    ),
    CommerceScenario(
        id="TC_HELDOUT_2",
        test_case=TestCase(
            id="TD3",
            input="Show me the Coffee Maker.",
            category="tool_contract_heldout",
            difficulty="medium",
            requirement_ids=["R_PRODUCT_LOOKUP", "R_TOOL_ARGUMENT_CONTRACT"],
        ),
        ground_truth=CommerceGroundTruth(expected_tool="search_products"),
    ),
    CommerceScenario(
        id="TC_HELDOUT_3",
        test_case=TestCase(
            id="TD4",
            input="帮我找一下跑鞋",
            category="tool_contract_heldout",
            difficulty="hard",
            requirement_ids=["R_PRODUCT_LOOKUP", "R_TOOL_ARGUMENT_CONTRACT"],
        ),
        ground_truth=CommerceGroundTruth(expected_tool="search_products"),
    ),
    CommerceScenario(
        id="TC_CONTROL",
        test_case=TestCase(
            id="TD5",
            input="Search for Running Shoes using the required query argument.",
            category="tool_contract_control",
            difficulty="medium",
            requirement_ids=["R_PRODUCT_LOOKUP", "R_TOOL_ARGUMENT_CONTRACT"],
        ),
        ground_truth=CommerceGroundTruth(expected_tool="search_products"),
    ),
)

TOOL_CONTRACT_SEED = TOOL_CONTRACT_CASES[0]
TOOL_CONTRACT_HELDOUT = TOOL_CONTRACT_CASES[1:4]
TOOL_CONTRACT_CONTROL = TOOL_CONTRACT_CASES[4]


class ContractSensitiveRouter:
    """Controlled router whose product arguments respond to Harness evidence.

    Promotion and eligibility routing mirrors the stable Commerce routing used
    elsewhere in the demo. Product lookup deliberately emits a legacy argument
    key until either the user explicitly requests the documented argument or
    the rendered tool description exposes the registered query contract.
    """

    explicit_contract_marker = 'Arguments: {"query":"<string>"}.'

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        user_input = prompt.rsplit("User input: ", 1)[1]
        lowered = user_input.casefold()

        eligibility = any(
            term in lowered for term in ("eligible", "eligibility", "qualify", "gift")
        )
        policy_match = re.search(r"policy_[a-z]", user_input, re.IGNORECASE)
        date_match = re.search(r"\\d{4}-\\d{2}-\\d{2}", user_input)
        amount_match = re.search(
            r"(?:amount|spend|paid|for|total)\\s*(?:is|of|:)?\\s*(\\d+)",
            lowered,
        )

        if eligibility:
            if policy_match is None and date_match is not None:
                return _route("search_policy", {"active_on": date_match.group(0)})
            arguments: dict[str, object] = {}
            if policy_match:
                arguments["policy_id"] = policy_match.group(0).upper()
            if date_match:
                arguments["purchase_date"] = date_match.group(0)
            if amount_match:
                arguments["purchase_amount"] = int(amount_match.group(1))
            return _route("check_eligibility", arguments)

        if "policy" in lowered or "promotion" in lowered:
            arguments = {}
            if policy_match:
                arguments["policy_id"] = policy_match.group(0).upper()
            if date_match:
                arguments["active_on"] = date_match.group(0)
            return _route("search_policy", arguments)

        contract_is_explicit = self.explicit_contract_marker in prompt
        explicit_control = "required query argument" in lowered
        argument_key = "query" if contract_is_explicit or explicit_control else "product_name"
        return _route("search_products", {argument_key: user_input})


@dataclass(frozen=True)
class ToolContractRepairProof:
    """Structured result for the seed/held-out/control repair experiment."""

    baseline_config: AgentConfig
    candidate_config: AgentConfig
    seed_trace: ExecutionTrace
    seed_evaluation: EvaluationResult
    failure_pattern: FailurePattern
    root_cause: RootCauseAnalysis
    patch: HarnessPatch
    baseline_traces: tuple[ExecutionTrace, ...]
    baseline_evaluations: tuple[EvaluationResult, ...]
    candidate_traces: tuple[ExecutionTrace, ...]
    candidate_evaluations: tuple[EvaluationResult, ...]
    regression_decision: RegressionDecision


def build_tool_contract_repair_proof(
    baseline_config: AgentConfig | None = None,
) -> ToolContractRepairProof:
    """Derive one patch from TD1, then validate it on unseen and frozen cases."""

    accepted_v2 = baseline_config or _accepted_workflow_candidate()

    seed_router = ContractSensitiveRouter()
    seed_trace = run_agent(
        TOOL_CONTRACT_SEED.test_case,
        accepted_v2,
        CommerceAgent(llm=seed_router),
    )
    seed_evaluation = evaluate_commerce(TOOL_CONTRACT_SEED, seed_trace)
    patterns = analyze_failures([seed_evaluation], [seed_trace], accepted_v2)
    if len(patterns) != 1:
        raise RuntimeError(
            "TD1 must produce exactly one evidence-backed failure pattern"
        )
    failure_pattern = patterns[0]
    root_cause = analyze_root_cause(
        failure_pattern,
        [seed_trace],
        accepted_v2,
    )
    patch = propose_harness_patch(
        failure_pattern,
        root_cause,
        accepted_v2,
    )
    candidate = apply_harness_patch(
        accepted_v2,
        patch,
        "commerce-v3-tool-description",
    )

    validation_scenarios = (*COMMERCE_SCENARIOS, *TOOL_CONTRACT_CASES)
    validation_router = ContractSensitiveRouter()
    validation_agent = CommerceAgent(llm=validation_router)

    baseline_traces = run_benchmark(
        [scenario.test_case for scenario in validation_scenarios],
        accepted_v2,
        validation_agent,
    )
    baseline_evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(validation_scenarios, baseline_traces, strict=True)
    ]
    candidate_traces = run_benchmark(
        [scenario.test_case for scenario in validation_scenarios],
        candidate,
        validation_agent,
    )
    candidate_evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(validation_scenarios, candidate_traces, strict=True)
    ]
    decision = compare_versions(
        baseline_evaluations,
        candidate_evaluations,
        baseline_traces=baseline_traces,
        candidate_traces=candidate_traces,
    )

    return ToolContractRepairProof(
        baseline_config=accepted_v2,
        candidate_config=candidate,
        seed_trace=seed_trace,
        seed_evaluation=seed_evaluation,
        failure_pattern=failure_pattern,
        root_cause=root_cause,
        patch=patch,
        baseline_traces=tuple(baseline_traces),
        baseline_evaluations=tuple(baseline_evaluations),
        candidate_traces=tuple(candidate_traces),
        candidate_evaluations=tuple(candidate_evaluations),
        regression_decision=decision,
    )


def _accepted_workflow_candidate() -> AgentConfig:
    first_cycle = run_optimization_cycle(
        COMMERCE_SCENARIOS,
        commerce_v1_config(),
        CommerceAgent(),
        evaluate_commerce,
        candidate_version="commerce-v2",
    )
    if (
        first_cycle.candidate_config is None
        or first_cycle.regression_decision is None
        or first_cycle.regression_decision.decision != "accept"
    ):
        raise RuntimeError("Accepted Commerce V2 workflow candidate is unavailable")
    return first_cycle.candidate_config


def _route(tool: str, arguments: dict[str, object]) -> str:
    return json.dumps({"tool": tool, "arguments": arguments})
