"""Commerce tool-interface diagnosis and bounded description patch tests."""

from app.debugger import analyze_failures
from app.optimizer import apply_harness_patch
from app.runner import run_agent
from app.schemas import EvaluationResult, ExecutionTrace
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    analyze_commerce_tool_argument_root_cause,
    commerce_v1_config,
    propose_commerce_tool_description_patch,
)
from app.targets.commerce.evaluator import evaluate_commerce


def _external_argument_failure():
    scenario = next(item for item in COMMERCE_SCENARIOS if item.id == "CS1")
    trace = ExecutionTrace(
        test_id=scenario.test_case.id,
        agent_version="commerce-v2",
        output='{"error":"product query is required"}',
        tool_calls=["search_products"],
        tool_call_arguments=[{"product_name": "Running Shoes"}],
        error="product query is required",
    )
    evaluation = EvaluationResult(
        test_id=trace.test_id,
        agent_version=trace.agent_version,
        passed=False,
        final_score=0.5,
        rule_scores={
            "execution_succeeded": 0.0,
            "required_tool_called": 1.0,
        },
        semantic_scores={},
        failed_requirement_ids=scenario.test_case.requirement_ids,
        explanation="Target execution returned an unexpected error.",
    )
    return scenario, trace, evaluation


def test_external_argument_key_failure_is_classified_from_trace() -> None:
    _, trace, evaluation = _external_argument_failure()

    config = commerce_v1_config().model_copy(update={"version": "commerce-v2"})
    patterns = analyze_failures([evaluation], [trace], config)

    assert patterns[0].category == "tool_argument_schema_failure"


def test_commerce_root_cause_and_patch_require_query_schema() -> None:
    scenario, trace, evaluation = _external_argument_failure()
    config = commerce_v1_config().model_copy(update={"version": "commerce-v2"})
    pattern = analyze_failures([evaluation], [trace], config)[0]

    root_cause = analyze_commerce_tool_argument_root_cause(
        pattern, [trace], config
    )
    patch = propose_commerce_tool_description_patch(pattern, root_cause, config)

    assert root_cause.target_component == "tool_description"
    assert '"query"' in patch.proposed_value["description"]
    assert "product_name" not in patch.proposed_value["description"]
    candidate = apply_harness_patch(config, patch, "commerce-v3-tool-schema")
    search_tool = next(tool for tool in candidate.tools if tool.name == "search_products")
    assert '"query"' in search_tool.description
    assert candidate.version == "commerce-v3-tool-schema"
