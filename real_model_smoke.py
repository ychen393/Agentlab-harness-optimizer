"""Optional external-model check; excluded from normal pytest execution."""

import argparse

from app.demo_evidence import build_demo_evidence
from app.llm import OpenAICompatibleChat
from app.runner import run_agent
from app.targets.commerce import CommerceAgent, evaluate_commerce


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
    agent = CommerceAgent(llm=client)
    counts = {"V2": 0, "V3": 0}
    for label, config in (("V2", v2), ("V3", v3)):
        for _ in range(args.repetitions):
            trace = run_agent(ex2.test_case, config, agent)
            evaluation = evaluate_commerce(ex2, trace)
            counts[label] += int(evaluation.passed)
    print(
        "External-model evidence (supplementary; same provider/model/input/evaluator):"
    )
    print(f"V2 correct routing: {counts['V2']}/{args.repetitions}")
    print(f"V3 correct routing: {counts['V3']}/{args.repetitions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
