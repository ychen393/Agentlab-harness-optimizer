"""Unit tests for the AgentLab MVP data contracts."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    FailurePattern,
    Requirement,
    RequirementSpec,
    RuleCheckResult,
    SemanticScore,
    TestCase as BenchmarkTestCase,
    ToolConfig,
    WorkflowConfig,
)


def example_requirement_spec() -> RequirementSpec:
    return RequirementSpec(
        task_type="research",
        task_description="Research recent Agent evaluation approaches",
        requirements=[
            Requirement(
                id="R1",
                description="Use recent sources",
                type="freshness",
                weight=0.5,
            ),
            Requirement(
                id="R2",
                description="Include citations",
                type="citation",
                weight=0.5,
            ),
        ],
    )


def example_test_case() -> BenchmarkTestCase:
    return BenchmarkTestCase(
        id="T07",
        input="Compare current agent evaluation approaches using recent sources.",
        category="fresh_information",
        difficulty="medium",
        requirement_ids=["R1", "R2"],
    )


def test_valid_objects_can_be_created() -> None:
    spec = example_requirement_spec()
    case = example_test_case()
    workflow = WorkflowConfig()
    agent = AgentConfig(
        version="V1",
        system_prompt="Produce an evidence-based research report.",
        tools=[ToolConfig(name="web_search", description="Search the web.")],
        workflow=workflow,
    )
    trace = ExecutionTrace(
        test_id=case.id,
        agent_version=agent.version,
        output="Report output",
        latency_seconds=1.2,
        input_tokens=10,
        output_tokens=20,
    )
    rule = RuleCheckResult(metric="output_not_empty", passed=True, score=1.0)
    semantic = SemanticScore(
        factuality=0.9,
        coverage=0.8,
        relevance=0.9,
        evidence_support=0.7,
        reasoning="The response is relevant and mostly supported.",
    )
    evaluation = EvaluationResult(
        test_id=trace.test_id,
        agent_version=trace.agent_version,
        passed=True,
        final_score=0.85,
        rule_scores={rule.metric: rule.score},
        semantic_scores={"factuality": semantic.factuality},
        failed_requirement_ids=[],
        explanation="Passed the configured threshold.",
    )

    assert spec.requirements[0].id == "R1"
    assert workflow.max_steps == 6
    assert workflow.require_citation is False
    assert agent.context == []
    assert trace.tool_calls == []
    assert evaluation.final_score == 0.85


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (
            Requirement,
            {"id": "R1", "description": "Bad type", "type": "unknown", "weight": 1},
        ),
        (
            BenchmarkTestCase,
            {
                "id": "T1",
                "input": "Input",
                "category": "unsupported",
                "difficulty": "easy",
                "requirement_ids": ["R1"],
            },
        ),
        (
            BenchmarkTestCase,
            {
                "id": "T1",
                "input": "Input",
                "category": "normal",
                "difficulty": "extreme",
                "requirement_ids": ["R1"],
            },
        ),
    ],
)
def test_invalid_literal_values_are_rejected(model: type, data: dict) -> None:
    with pytest.raises(ValidationError):
        model(**data)


@pytest.mark.parametrize("weight", [-0.01, 1.01])
def test_requirement_weight_must_be_normalized(weight: float) -> None:
    with pytest.raises(ValidationError):
        Requirement(id="R1", description="Criterion", type="other", weight=weight)


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_rule_and_final_scores_must_be_normalized(score: float) -> None:
    with pytest.raises(ValidationError):
        RuleCheckResult(metric="check", passed=False, score=score)
    with pytest.raises(ValidationError):
        EvaluationResult(
            test_id="T1",
            agent_version="V1",
            passed=False,
            final_score=score,
            rule_scores={},
            semantic_scores={},
            failed_requirement_ids=["R1"],
            explanation="Failed",
        )


@pytest.mark.parametrize(
    "field", ["factuality", "coverage", "relevance", "evidence_support"]
)
@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_each_semantic_score_must_be_normalized(field: str, score: float) -> None:
    values = {
        "factuality": 0.5,
        "coverage": 0.5,
        "relevance": 0.5,
        "evidence_support": 0.5,
        "reasoning": "Reason",
    }
    values[field] = score

    with pytest.raises(ValidationError):
        SemanticScore(**values)


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_evaluation_rule_score_values_must_be_normalized(score: float) -> None:
    with pytest.raises(ValidationError):
        EvaluationResult(
            test_id="T1",
            agent_version="V1",
            passed=False,
            final_score=0.5,
            rule_scores={"output_not_empty": score},
            semantic_scores={},
            failed_requirement_ids=["R1"],
            explanation="Failed",
        )


def test_test_case_requires_at_least_one_requirement_id() -> None:
    with pytest.raises(ValidationError):
        BenchmarkTestCase(
            id="T1",
            input="Input",
            category="normal",
            difficulty="easy",
            requirement_ids=[],
        )


@pytest.mark.parametrize("version", ["", "   "])
def test_agent_version_cannot_be_blank(version: str) -> None:
    with pytest.raises(ValidationError):
        AgentConfig(
            version=version,
            system_prompt="Prompt",
            tools=[],
            workflow=WorkflowConfig(),
        )


@pytest.mark.parametrize("max_steps", [0, -1])
def test_workflow_max_steps_must_be_positive(max_steps: int) -> None:
    with pytest.raises(ValidationError):
        WorkflowConfig(max_steps=max_steps)


@pytest.mark.parametrize(
    "values",
    [
        {"latency_seconds": -0.1},
        {"input_tokens": -1},
        {"output_tokens": -1},
    ],
)
def test_negative_execution_metrics_are_rejected(values: dict) -> None:
    with pytest.raises(ValidationError):
        ExecutionTrace(test_id="T1", agent_version="V1", output="", **values)


@pytest.mark.parametrize("field", ["test_id", "agent_version"])
def test_required_execution_identifiers_cannot_be_empty(field: str) -> None:
    data = {"test_id": "T1", "agent_version": "V1", "output": "output"}
    data[field] = "   "
    with pytest.raises(ValidationError):
        ExecutionTrace(**data)


def test_required_fields_are_enforced() -> None:
    with pytest.raises(ValidationError):
        Requirement(id="R1", description="Missing weight", type="coverage")
    with pytest.raises(ValidationError):
        BenchmarkTestCase(
            id="T1",
            input="Missing difficulty",
            category="normal",
            requirement_ids=["R1"],
        )
    with pytest.raises(ValidationError):
        AgentConfig(version="V1", system_prompt="Prompt", tools=[])


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (
            Requirement,
            {"id": " ", "description": "Criterion", "type": "other", "weight": 1},
        ),
        (
            BenchmarkTestCase,
            {
                "id": "",
                "input": "Input",
                "category": "normal",
                "difficulty": "easy",
                "requirement_ids": ["R1"],
            },
        ),
    ],
)
def test_required_ids_cannot_be_empty(model: type, data: dict) -> None:
    with pytest.raises(ValidationError):
        model(**data)


@pytest.mark.parametrize("factory", [example_requirement_spec, example_test_case])
def test_examples_round_trip_through_json(factory) -> None:
    original = factory()
    restored = type(original).model_validate_json(original.model_dump_json())
    assert restored == original


def test_mutable_defaults_are_not_shared() -> None:
    first = WorkflowConfig()
    first_agent = AgentConfig(
        version="V1", system_prompt="Prompt", tools=[], workflow=first
    )
    second_agent = AgentConfig(
        version="V2", system_prompt="Prompt", tools=[], workflow=WorkflowConfig()
    )
    first_agent.context.append("context")

    first_trace = ExecutionTrace(test_id="T1", agent_version="V1", output="")
    second_trace = ExecutionTrace(test_id="T2", agent_version="V1", output="")
    first_trace.tool_calls.append("web_search")

    assert second_agent.context == []
    assert second_trace.tool_calls == []


def test_failure_pattern_has_stable_nonempty_id() -> None:
    pattern = FailurePattern(
        id="F1",
        category="policy_violation",
        count=2,
        affected_test_ids=["T1", "T3"],
        severity="high",
        summary="The target agent repeatedly violated the return policy.",
    )

    assert pattern.id == "F1"


@pytest.mark.parametrize("pattern_id", ["", "   "])
def test_failure_pattern_id_cannot_be_blank(pattern_id: str) -> None:
    with pytest.raises(ValidationError):
        FailurePattern(
            id=pattern_id,
            category="policy_violation",
            count=1,
            affected_test_ids=["T1"],
            severity="high",
            summary="Policy violation.",
        )
