"""Tests for the provider-neutral Requirement Parser."""

import json

import pytest

from app.requirement import RequirementParseError, parse_requirement
from app.schemas import RequirementSpec


class MockLLM:
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def llm_json(requirements: list[dict], task_type: str = "research") -> str:
    return json.dumps(
        {
            "task_type": task_type,
            "task_description": "Extracted description",
            "requirements": requirements,
        }
    )


def requirement(
    description: str,
    requirement_type: str = "other",
    weight: float = 1.0,
    requirement_id: str = "model-generated-id",
) -> dict:
    return {
        "id": requirement_id,
        "description": description,
        "type": requirement_type,
        "weight": weight,
    }


def test_valid_single_requirement() -> None:
    raw_text = "Build a research agent that uses recent sources."
    result = parse_requirement(
        raw_text,
        MockLLM(llm_json([requirement("Use recent sources", "freshness")])),
    )

    assert isinstance(result, RequirementSpec)
    assert result.task_description == raw_text
    assert result.requirements[0].description == "Use recent sources"


def test_multiple_requirements_receive_stable_ids() -> None:
    result = parse_requirement(
        "Use recent sources, include citations, and produce a structured report.",
        MockLLM(
            llm_json(
                [
                    requirement("Use recent sources", "freshness", 0.3, "A"),
                    requirement("Include citations", "citation", 0.4, "B"),
                    requirement("Produce a structured report", "format", 0.3, "C"),
                ]
            )
        ),
    )

    assert [item.id for item in result.requirements] == ["R1", "R2", "R3"]
    assert len(result.requirements) == 3


def test_requirement_types_and_weights_are_valid() -> None:
    result = parse_requirement(
        "Use recent sources and cite them.",
        MockLLM(
            llm_json(
                [
                    requirement("Use recent sources", "freshness", 0.5),
                    requirement("Cite the sources", "citation", 0.5),
                ]
            )
        ),
    )

    allowed_types = {
        "freshness",
        "citation",
        "factuality",
        "coverage",
        "format",
        "tool_usage",
        "other",
    }
    assert all(item.type in allowed_types for item in result.requirements)
    assert all(0 <= item.weight <= 1 for item in result.requirements)


@pytest.mark.parametrize("raw_text", ["", "   "])
def test_empty_input_is_rejected_without_calling_llm(raw_text: str) -> None:
    llm = MockLLM()

    with pytest.raises(ValueError, match="non-empty"):
        parse_requirement(raw_text, llm)

    assert llm.prompts == []


def test_malformed_llm_output_is_retried_once() -> None:
    llm = MockLLM(
        "not JSON",
        llm_json([requirement("Include five citations", "citation")]),
    )

    result = parse_requirement("Include five citations.", llm)

    assert result.requirements[0].type == "citation"
    assert len(llm.prompts) == 2
    assert "previous extraction was invalid" in llm.prompts[1]


def test_repeated_malformed_llm_output_raises_explicit_error() -> None:
    llm = MockLLM("not JSON", "still not JSON")

    with pytest.raises(RequirementParseError, match="after one correction retry"):
        parse_requirement("Use recent sources.", llm)

    assert len(llm.prompts) == 2


def test_schema_validation_failure_retries_then_raises() -> None:
    missing_type = llm_json(
        [{"id": "R1", "description": "Use recent sources", "weight": 1.0}]
    )
    unsupported_type = llm_json(
        [requirement("Use recent sources", "unsupported", 1.0)]
    )
    llm = MockLLM(missing_type, unsupported_type)

    with pytest.raises(RequirementParseError, match="RequirementSpec"):
        parse_requirement("Use recent sources.", llm)

    assert len(llm.prompts) == 2


def test_empty_requirement_list_is_rejected() -> None:
    llm = MockLLM(llm_json([]), llm_json([]))

    with pytest.raises(RequirementParseError, match="at least one"):
        parse_requirement("Research agent evaluation.", llm)


def test_parser_does_not_add_unsupported_requirements() -> None:
    raw_text = "Include at least five citations."
    llm = MockLLM(
        llm_json([requirement("Include at least five citations", "citation")])
    )

    result = parse_requirement(raw_text, llm)

    assert [item.description for item in result.requirements] == [
        "Include at least five citations"
    ]
    assert result.task_description == raw_text
    assert "Include only requirements supported" in llm.prompts[0]
