"""Optional external-model check; excluded from normal pytest execution."""

import argparse
import json
from pathlib import Path
from collections import Counter
from collections.abc import Callable
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.demo_evidence import build_demo_evidence
from app.llm import OpenAICompatibleChat
from app.runner import run_agent
from app.targets.commerce import CommerceAgent, evaluate_commerce


class CapturingLLM:
    """Capture one provider response while returning it completely unchanged."""

    def __init__(self, llm: Callable[[str], str]) -> None:
        self._llm = llm
        self.raw_response: str | None = None

    def __call__(self, prompt: str) -> str:
        self.raw_response = None
        response = self._llm(prompt)
        self.raw_response = response
        return response


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare V2 and V3 routing on EX2 using one external model."
    )
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if args.repetitions <= 0:
        parser.error("--repetitions must be greater than 0")

    try:
        client = OpenAICompatibleChat.from_env()
    except ValueError as error:
        print(f"External-model smoke test not run: {error}")
        return 2

    evidence = build_demo_evidence()
    v2 = evidence.first_cycle.candidate_config
    v3 = evidence.second_cycle.candidate_config
    if v2 is None or v3 is None:
        print("External-model smoke test not run: V2/V3 configs are unavailable.")
        return 2
    ex2 = next(
        scenario
        for scenario in evidence.coverage_report.generated_challenges
        if scenario.id == "EX2"
    )
    capturing_client = CapturingLLM(client)
    agent = CommerceAgent(llm=capturing_client)
    counts = {
        "V2": {"correct_tool_selection": 0, "scenario_pass": 0},
        "V3": {"correct_tool_selection": 0, "scenario_pass": 0},
    }
    observations = {"V2": Counter(), "V3": Counter()}
    for label, config in (("V2", v2), ("V3", v3)):
        for repetition in range(1, args.repetitions + 1):
            trace = run_agent(ex2.test_case, config, agent)
            evaluation = evaluate_commerce(ex2, trace)
            correct_tool_selection = "search_products" in trace.tool_calls
            counts[label]["correct_tool_selection"] += int(correct_tool_selection)
            counts[label]["scenario_pass"] += int(evaluation.passed)
            _update_observations(observations[label], trace, evaluation.passed)
            _print_diagnostic(
                label,
                repetition,
                client.model,
                capturing_client.raw_response,
                trace,
                evaluation,
                correct_tool_selection,
            )
    print(
        "External-model evidence (supplementary; same provider/model/input/evaluator):"
    )
    for label in ("V2", "V3"):
        print(
            f"{label} correct tool selection: "
            f"{counts[label]['correct_tool_selection']}/{args.repetitions}"
        )
        print(
            f"{label} scenario pass: "
            f"{counts[label]['scenario_pass']}/{args.repetitions}"
        )
    for label in ("V2", "V3"):
        print(f"{label} observed behavior counts:")
        for reason in (
            "invalid_router_json",
            "search_policy_selected",
            "search_products_selected",
            "other_tool_selected",
            "no_tool_selected",
            "execution_error",
            "passed",
            "failed",
        ):
            print(f"- {reason}: {observations[label][reason]}")
    return 0


def _print_diagnostic(
    label: str,
    repetition: int,
    model: str,
    raw_response: str | None,
    trace,
    evaluation,
    correct_tool_selection: bool,
) -> None:
    if raw_response is None and not trace.tool_calls and trace.error:
        print(f"=== {label} repetition {repetition} ===")
        print(f"model: {model}")
        print("failure_category: API_REQUEST_ERROR")
        print(f"trace.error: {trace.error}")
        return
    print(
        json.dumps(
            _diagnostic_record(
                label,
                repetition,
                raw_response,
                trace,
                evaluation,
                correct_tool_selection,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _diagnostic_record(
    label: str,
    repetition: int,
    raw_response: str | None,
    trace,
    evaluation,
    correct_tool_selection: bool,
) -> dict[str, object]:
    failed_rules = {
        name: score
        for name, score in evaluation.rule_scores.items()
        if score < 1.0
    }
    return {
        "version": label,
        "repetition": repetition,
        "raw_model_response": raw_response,
        "tool_calls": trace.tool_calls,
        "error": trace.error,
        "output": trace.output,
        "passed": evaluation.passed,
        "correct_tool_selection": correct_tool_selection,
        "scenario_pass": evaluation.passed,
        "failed_rule_checks": failed_rules,
        "rule_scores": evaluation.rule_scores,
        "explanation": evaluation.explanation,
    }


def _update_observations(
    counts: Counter[str], trace, passed: bool
) -> None:
    if trace.error and "router must return a JSON object" in trace.error:
        counts["invalid_router_json"] += 1
    if "search_policy" in trace.tool_calls:
        counts["search_policy_selected"] += 1
    if "search_products" in trace.tool_calls:
        counts["search_products_selected"] += 1
    if trace.tool_calls and not {
        "search_policy",
        "search_products",
    }.intersection(trace.tool_calls):
        counts["other_tool_selected"] += 1
    if not trace.tool_calls:
        counts["no_tool_selected"] += 1
    if trace.error is not None:
        counts["execution_error"] += 1
    counts["passed" if passed else "failed"] += 1


if __name__ == "__main__":
    raise SystemExit(main())
