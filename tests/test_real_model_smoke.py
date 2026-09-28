"""Offline tests for external smoke-test diagnostics."""

from collections import Counter

from app.schemas import EvaluationResult, ExecutionTrace
from scripts.real_model_smoke import CapturingLLM, _diagnostic_record, _update_observations


def test_capturing_llm_preserves_exact_raw_response() -> None:
    raw = "```json\n{\"tool\": \"search_products\", \"arguments\": {}}\n```"
    wrapper = CapturingLLM(lambda prompt: raw)

    returned = wrapper("prompt")

    assert returned == raw
    assert wrapper.raw_response == raw


def test_diagnostic_record_reports_failed_rules_without_secrets() -> None:
    trace = ExecutionTrace(
        test_id="EXT2",
        agent_version="commerce-v2",
        output='{"error": "router must return a JSON object"}',
        error="router must return a JSON object",
    )
    evaluation = EvaluationResult(
        test_id="EXT2",
        agent_version="commerce-v2",
        passed=False,
        final_score=0.0,
        rule_scores={"execution_succeeded": 0.0, "required_tool_called": 0.0},
        semantic_scores={},
        failed_requirement_ids=["R_TOOL_SELECTION"],
        explanation="Target execution returned an unexpected error.",
    )

    record = _diagnostic_record(
        "V2", 1, "```json\n{}\n```", trace, evaluation, False
    )

    assert record["raw_model_response"] == "```json\n{}\n```"
    assert record["failed_rule_checks"] == evaluation.rule_scores
    assert record["correct_tool_selection"] is False
    assert record["scenario_pass"] is False
    assert "api_key" not in record
    assert "authorization" not in record


def test_observation_counts_are_derived_from_trace() -> None:
    counts = Counter()
    trace = ExecutionTrace(
        test_id="EXT2",
        agent_version="commerce-v2",
        output='{"error": "router must return a JSON object"}',
        error="router must return a JSON object",
    )

    _update_observations(counts, trace, passed=False)

    assert counts == Counter(
        {
            "invalid_router_json": 1,
            "no_tool_selected": 1,
            "execution_error": 1,
            "failed": 1,
        }
    )
