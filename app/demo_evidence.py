"""In-memory evidence preparation shared by the CLI and Streamlit demos."""

import json
import re
from dataclasses import dataclass

from app.optimizer import run_optimization_cycle
from app.schemas import (
    EvaluationResult,
    ExecutionTrace,
    OptimizationCycleResult,
    RegressionDecision,
)
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
from app.targets.commerce.domain_models import (
    CommerceCoverageReport,
    CommerceScenario,
)


class ControlledDemoRouter:
    """Provider-independent router used only for controlled demo evidence."""

    patch_marker = "Honor explicit exclusions and negated intent"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        user_input = prompt.rsplit("User input: ", 1)[1]
        lowered = user_input.casefold()

        if "running shoes" in lowered and "promotion" in lowered:
            if self.patch_marker in prompt:
                return _route("search_products", {"query": "Running Shoes"})
            return _route("search_policy", {"policy_id": "POLICY_A"})

        eligibility = any(
            term in lowered
            for term in ("eligible", "eligibility", "qualify", "gift")
        )
        policy_match = re.search(r"policy_[a-z]", user_input, re.IGNORECASE)
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", user_input)
        amount_match = re.search(
            r"(?:amount|spend|paid|for|total)\s*(?:is|of|:)?\s*(\d+)",
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
        return _route("search_products", {"query": user_input})


@dataclass(frozen=True)
class DemoEvidence:
    first_cycle: OptimizationCycleResult
    adaptive_challenges: tuple[CommerceScenario, ...]
    coverage_report: CommerceCoverageReport
    deterministic_patchability: OptimizationCycleResult
    second_cycle: OptimizationCycleResult
    validation_baseline_traces: tuple[ExecutionTrace, ...]
    validation_baseline_evaluations: tuple[EvaluationResult, ...]
    validation_candidate_traces: tuple[ExecutionTrace, ...]
    validation_candidate_evaluations: tuple[EvaluationResult, ...]
    final_decision: RegressionDecision


def build_demo_evidence() -> DemoEvidence:
    """Execute the existing optimization APIs and retain their real outputs."""

    first_cycle = run_optimization_cycle(
        COMMERCE_SCENARIOS,
        commerce_v1_config(),
        CommerceAgent(),
        evaluate_commerce,
        candidate_version="commerce-v2",
    )
    if first_cycle.candidate_config is None:
        raise RuntimeError(f"V2 was not produced: {first_cycle.message}")

    adaptive = tuple(
        generate_challenges(
            first_cycle.failure_patterns,
            first_cycle.root_cause_analyses,
            COMMERCE_SCENARIOS,
        )
    )
    coverage = analyze_coverage(COMMERCE_SCENARIOS, adaptive)
    ex2 = next(
        scenario for scenario in coverage.generated_challenges if scenario.id == "EX2"
    )
    patchability = assess_deterministic_patchability(
        ex2, first_cycle.candidate_config
    )
    second_cycle = run_harness_sensitive_cycle(
        ex2,
        first_cycle.candidate_config,
        ControlledDemoRouter(),
        candidate_version="commerce-v3",
    )
    if second_cycle.candidate_config is None:
        raise RuntimeError(f"V3 was not produced: {second_cycle.message}")

    baseline_traces, baseline_evaluations, candidate_traces, candidate_evaluations, decision = (
        validate_harness_candidate(
            COMMERCE_SCENARIOS,
            adaptive,
            coverage.generated_challenges,
            first_cycle.candidate_config,
            second_cycle.candidate_config,
            ControlledDemoRouter(),
        )
    )
    return DemoEvidence(
        first_cycle=first_cycle,
        adaptive_challenges=adaptive,
        coverage_report=coverage,
        deterministic_patchability=patchability,
        second_cycle=second_cycle,
        validation_baseline_traces=tuple(baseline_traces),
        validation_baseline_evaluations=tuple(baseline_evaluations),
        validation_candidate_traces=tuple(candidate_traces),
        validation_candidate_evaluations=tuple(candidate_evaluations),
        final_decision=decision,
    )


def evolution_rows(evidence: DemoEvidence) -> list[dict[str, object]]:
    """Prepare compact pass-rate rows without altering source results."""

    first = evidence.first_cycle
    return [
        _result_row("Fixed regression", "V1", first.baseline_evaluations),
        _result_row("Fixed regression", "V2", first.candidate_evaluations),
        _result_row(
            "All CT + AC + EX",
            "V2",
            evidence.validation_baseline_evaluations,
        ),
        _result_row(
            "All CT + AC + EX",
            "V3",
            evidence.validation_candidate_evaluations,
        ),
    ]


def validation_rows(evidence: DemoEvidence) -> list[dict[str, object]]:
    """Separate fixed, adaptive, and exploratory validation evidence."""

    groups = {
        "Fixed Regression Set (CT1-CT7)": {
            scenario.test_case.id for scenario in COMMERCE_SCENARIOS
        },
        "Adaptive Challenge Set (AC1-AC5)": {
            scenario.test_case.id for scenario in evidence.adaptive_challenges
        },
        "Coverage Exploration Set (EX1-EX4)": {
            scenario.test_case.id
            for scenario in evidence.coverage_report.generated_challenges
        },
    }
    rows: list[dict[str, object]] = []
    for name, test_ids in groups.items():
        baseline = [
            item
            for item in evidence.validation_baseline_evaluations
            if item.test_id in test_ids
        ]
        candidate = [
            item
            for item in evidence.validation_candidate_evaluations
            if item.test_id in test_ids
        ]
        rows.append(
            {
                "test_set": name,
                "purpose": _test_set_purpose(name),
                "v2": f"{sum(item.passed for item in baseline)}/{len(baseline)}",
                "v3": f"{sum(item.passed for item in candidate)}/{len(candidate)}",
            }
        )
    return rows


def format_cli_report(evidence: DemoEvidence) -> str:
    """Render the complete verified story as a readable text report."""

    first = evidence.first_cycle
    second = evidence.second_cycle
    patch1 = first.proposed_patch
    patch2 = second.proposed_patch
    ex2_baseline = second.baseline_traces[0]
    ex2_candidate = second.candidate_traces[0]
    lines = [
        "AgentLab - Demo and Evidence Layer",
        "=" * 36,
        "Evidence boundary: deterministic Commerce evidence and provider-independent mock-router evidence are shown separately.",
        "",
        "1. V1 baseline [deterministic]",
        _pass_line(first.baseline_evaluations),
        "",
        "2. Failure pattern [deterministic]",
        _model_line(first.failure_patterns[0]),
        "",
        "3. Root cause [deterministic]",
        _model_line(first.root_cause_analyses[0]),
        "",
        "4. HarnessPatch #1 [deterministic]",
        _patch_line(patch1),
        "",
        "5. V2 regression [deterministic]",
        f"{_pass_line(first.candidate_evaluations)} Decision: {first.regression_decision.decision.upper()}.",
        "",
        "6. Adaptive challenges [deterministic]",
        "AC1-AC5 generated separately from failure evidence (5 scenarios).",
        "",
        "7. Coverage exploration [deterministic generation]",
        f"Covered: {', '.join(evidence.coverage_report.covered_dimensions)}",
        f"Undercovered: {', '.join(evidence.coverage_report.undercovered_dimensions)}",
        "Generated separately: EX1-EX4.",
        "",
        "8. EX2 weakness [deterministic]",
        f"EXT2 tools={evidence.deterministic_patchability.baseline_traces[0].tool_calls}; PASS=False.",
        "",
        "9. Patchability result [deterministic]",
        f"{evidence.deterministic_patchability.status}: {evidence.deterministic_patchability.message}",
        "",
        "10. HarnessPatch #2 [provider-independent mock router]",
        f"V2 EXT2 tools={ex2_baseline.tool_calls}; PASS={second.baseline_evaluations[0].passed}.",
        _patch_line(patch2),
        "",
        "11. V3 validation [provider-independent mock router]",
        f"V3 EXT2 tools={ex2_candidate.tool_calls}; PASS={second.candidate_evaluations[0].passed}.",
    ]
    lines.extend(
        f"{row['test_set']}: V2 {row['v2']} -> V3 {row['v3']}"
        for row in validation_rows(evidence)
    )
    lines.extend(
        [
            "",
            "12. Final decision [derived from actual mock-router execution]",
            (
                f"{evidence.final_decision.decision.upper()}: "
                f"{evidence.final_decision.explanation}"
            ),
            "",
            "Optional external-model evidence: not run by this deterministic CLI. Use real_model_smoke.py with explicit environment configuration.",
        ]
    )
    return "\n".join(lines)


def _route(tool: str, arguments: dict[str, object]) -> str:
    return json.dumps({"tool": tool, "arguments": arguments})


def _result_row(
    test_set: str,
    version: str,
    evaluations: tuple[EvaluationResult, ...] | list[EvaluationResult],
) -> dict[str, object]:
    passed = sum(item.passed for item in evaluations)
    total = len(evaluations)
    return {
        "test_set": test_set,
        "version": version,
        "passed": passed,
        "total": total,
        "pass_rate": passed / total,
    }


def _pass_line(evaluations: list[EvaluationResult]) -> str:
    passed = sum(item.passed for item in evaluations)
    return f"PASS {passed}/{len(evaluations)}"


def _model_line(model: object) -> str:
    return json.dumps(model.model_dump(), sort_keys=True)


def _patch_line(patch: object | None) -> str:
    if patch is None:
        return "No patch produced."
    values = patch.model_dump()
    return (
        f"target={values['target_component']}; "
        f"old={values['old_value']}; proposed={values['proposed_value']}"
    )


def _test_set_purpose(name: str) -> str:
    if name.startswith("Fixed"):
        return "Verify existing capability does not regress."
    if name.startswith("Adaptive"):
        return "Probe adjacent known weaknesses."
    return "Search previously under-tested behavior."
