"""Domain-independent tool-contract validation and patch tests."""

from app.debugger import analyze_failures, analyze_root_cause, validate_tool_arguments
from app.optimizer import ToolArgumentSchemaPatchStrategy
from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    ToolConfig,
    WorkflowConfig,
)


def weather_config() -> AgentConfig:
    return AgentConfig(
        version="weather-v1",
        system_prompt="Use the registered weather tool.",
        tools=[
            ToolConfig(
                name="weather_lookup",
                description="Look up the weather.",
                argument_schema={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "unit": {"type": "string"},
                    },
                    "required": ["city", "unit"],
                },
            )
        ],
        workflow=WorkflowConfig(max_steps=3),
    )


def weather_trace(arguments: dict[str, object]) -> ExecutionTrace:
    return ExecutionTrace(
        test_id="WEATHER-1",
        agent_version="weather-v1",
        output="tool failed",
        tool_calls=["weather_lookup"],
        tool_call_arguments=[arguments],
        error="tool arguments rejected",
    )


def failed_evaluation() -> EvaluationResult:
    return EvaluationResult(
        test_id="WEATHER-1",
        agent_version="weather-v1",
        passed=False,
        final_score=0.0,
        rule_scores={"execution_succeeded": 0.0},
        semantic_scores={},
        failed_requirement_ids=["R1"],
        explanation="Tool arguments were invalid.",
    )


def test_tool_contract_exposes_required_argument_names() -> None:
    contract = weather_config().tools[0]

    assert contract.argument_schema["required"] == ["city", "unit"]
    assert set(contract.argument_schema["properties"]) == {"city", "unit"}


def test_valid_tool_arguments_pass_validation() -> None:
    result = validate_tool_arguments(
        weather_config().tools[0], {"city": "Vancouver", "unit": "celsius"}
    )

    assert result.valid is True
    assert result.missing_required_arguments == []
    assert result.unexpected_arguments == []


def test_missing_and_unexpected_tool_arguments_are_reported() -> None:
    result = validate_tool_arguments(
        weather_config().tools[0], {"location": "Vancouver"}
    )

    assert result.valid is False
    assert result.missing_required_arguments == ["city", "unit"]
    assert result.unexpected_arguments == ["location"]


def test_generic_classifier_detects_contract_violation() -> None:
    config = weather_config()
    patterns = analyze_failures(
        [failed_evaluation()], [weather_trace({"location": "Vancouver"})], config
    )

    assert patterns[0].category == "tool_argument_schema_failure"


def test_generic_root_cause_targets_tool_description_without_domain_language() -> None:
    config = weather_config()
    trace = weather_trace({"location": "Vancouver"})
    pattern = analyze_failures([failed_evaluation()], [trace], config)[0]

    root_cause = analyze_root_cause(pattern, [trace], config)

    assert root_cause.target_component == "tool_description"
    assert root_cause.metadata["tool_name"] == "weather_lookup"
    assert "city" in " ".join(root_cause.evidence)
    assert "unit" in " ".join(root_cause.evidence)
    assert "Commerce" not in root_cause.root_cause


def test_generic_patch_derives_weather_schema_from_metadata() -> None:
    config = weather_config()
    trace = weather_trace({"location": "Vancouver"})
    pattern = analyze_failures([failed_evaluation()], [trace], config)[0]
    root_cause = analyze_root_cause(pattern, [trace], config)

    patch = ToolArgumentSchemaPatchStrategy().propose(pattern, root_cause, config)

    assert patch is not None
    assert patch.target_component == "tool_description"
    assert '"city":"<string>"' in patch.proposed_value["description"]
    assert '"unit":"<string>"' in patch.proposed_value["description"]
    assert "Commerce" not in patch.proposed_value["description"]


def test_missing_contract_returns_no_patch() -> None:
    config = weather_config().model_copy(update={"tools": []})
    pattern = analyze_failures(
        [failed_evaluation()], [weather_trace({"location": "Vancouver"})], weather_config()
    )[0]
    root_cause = analyze_root_cause(pattern, [weather_trace({"location": "Vancouver"})], weather_config())

    assert ToolArgumentSchemaPatchStrategy().propose(pattern, root_cause, config) is None


def test_non_editable_target_returns_no_patch() -> None:
    config = weather_config()
    trace = weather_trace({"location": "Vancouver"})
    pattern = analyze_failures([failed_evaluation()], [trace], config)[0]
    root_cause = analyze_root_cause(
        pattern, [trace], config
    ).model_copy(update={"target_component": "context"})

    assert ToolArgumentSchemaPatchStrategy().propose(pattern, root_cause, config) is None
