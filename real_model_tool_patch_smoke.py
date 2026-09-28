"""Optional external validation of the Commerce tool-schema description patch."""

import json

from app.debugger import analyze_failures
from app.llm import OpenAICompatibleChat
from app.optimizer import apply_harness_patch
from app.runner import run_agent
from app.targets.commerce import (
    CommerceAgent,
    analyze_commerce_tool_argument_root_cause,
    evaluate_commerce,
    propose_commerce_tool_description_patch,
)
from app.demo_evidence import build_demo_evidence
from real_model_smoke import CapturingLLM


def main() -> int:
    try:
        client = OpenAICompatibleChat.from_env()
    except ValueError as error:
        print(f"External-model tool-schema test not run: {error}")
        return 2

    evidence = build_demo_evidence()
    current_config = evidence.second_cycle.candidate_config
    if current_config is None:
        print("External-model tool-schema test not run: current config unavailable.")
        return 2
    ex2 = next(
        scenario
        for scenario in evidence.coverage_report.generated_challenges
        if scenario.id == "EX2"
    )
    capturing_client = CapturingLLM(client)
    agent = CommerceAgent(llm=capturing_client)
    current_trace = run_agent(ex2.test_case, current_config, agent)
    current_evaluation = evaluate_commerce(ex2, current_trace)
    _print_result("current", client.model, capturing_client.raw_response, current_trace, current_evaluation)

    if current_evaluation.passed:
        print("No tool-description patch proposed: current configuration passed EX2.")
        return 0

    patterns = analyze_failures([current_evaluation], [current_trace])
    if not patterns or patterns[0].category != "tool_argument_schema_failure":
        print("No tool-description patch proposed: failure evidence does not support it.")
        return 0
    root_cause = analyze_commerce_tool_argument_root_cause(
        patterns[0], [current_trace], current_config
    )
    patch = propose_commerce_tool_description_patch(
        patterns[0], root_cause, current_config
    )
    candidate_config = apply_harness_patch(
        current_config, patch, "commerce-v3-tool-schema"
    )
    candidate_trace = run_agent(ex2.test_case, candidate_config, agent)
    candidate_evaluation = evaluate_commerce(ex2, candidate_trace)
    _print_result(
        "candidate",
        client.model,
        capturing_client.raw_response,
        candidate_trace,
        candidate_evaluation,
    )
    print("patch.target_component: tool_description")
    print(json.dumps(patch.proposed_value, ensure_ascii=False, sort_keys=True))
    return 0


def _print_result(label, model, raw_response, trace, evaluation) -> None:
    print(f"=== {label} ===")
    print(f"model: {model}")
    print(f"raw_model_response: {raw_response}")
    print(f"trace.tool_calls: {trace.tool_calls}")
    print(f"trace.error: {trace.error}")
    print(f"trace.output: {trace.output}")
    print(f"evaluation.passed: {evaluation.passed}")
    print(f"evaluation.rule_scores: {evaluation.rule_scores}")
    print(f"evaluation.explanation: {evaluation.explanation}")


if __name__ == "__main__":
    raise SystemExit(main())
