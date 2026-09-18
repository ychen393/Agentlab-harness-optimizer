"""Unit tests for provider-neutral benchmark generation."""

import json

import pytest

from app.benchmark import BenchmarkGenerationError, generate_tests
from app.schemas import Requirement, RequirementSpec, TestCase as BenchmarkTestCase


class MockLLM:
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def requirement_spec() -> RequirementSpec:
    return RequirementSpec(
        task_type="research",
        task_description="Research current AI Agent evaluation approaches.",
        requirements=[
            Requirement(
                id="R1",
                description="Use recent sources",
                type="freshness",
                weight=0.3,
            ),
            Requirement(
                id="R2",
                description="Include at least five citations",
                type="citation",
                weight=0.3,
            ),
            Requirement(
                id="R3",
                description="Compare at least three approaches",
                type="coverage",
                weight=0.4,
            ),
        ],
    )


def three_category_requirement_spec() -> RequirementSpec:
    spec = requirement_spec()
    return spec.model_copy(
        update={
            "requirements": [
                *spec.requirements,
                Requirement(
                    id="R4",
                    description="Produce a structured report",
                    type="format",
                    weight=0.1,
                ),
            ]
        }
    )


def case(
    test_input: str,
    category: str,
    difficulty: str,
    requirement_ids: list[str],
    test_id: str = "LLM-ID",
) -> dict:
    return {
        "id": test_id,
        "input": test_input,
        "category": category,
        "difficulty": difficulty,
        "requirement_ids": requirement_ids,
    }


def valid_cases() -> list[dict]:
    return [
        case(
            "Summarize current agent evaluation methods using recent sources.",
            "fresh_information",
            "easy",
            ["R1"],
            "random-a",
        ),
        case(
            "Compare three evaluation approaches and provide five citations.",
            "citation_heavy",
            "medium",
            ["R2", "R3"],
            "random-b",
        ),
        case(
            "Assess conflicting evidence about three agent evaluation frameworks.",
            "adversarial",
            "hard",
            ["R1", "R2", "R3"],
            "random-c",
        ),
    ]


def as_json(cases: list[dict]) -> str:
    return json.dumps(cases)


def test_valid_benchmark_generation() -> None:
    result = generate_tests(requirement_spec(), MockLLM(as_json(valid_cases())), 3)

    assert all(isinstance(item, BenchmarkTestCase) for item in result)
    assert len(result) == 3


def test_generation_prompt_uses_target_agent_terminology() -> None:
    llm = MockLLM(as_json(valid_cases()))

    generate_tests(requirement_spec(), llm, 3)

    assert "test prompt for the Target Agent" in llm.prompts[0]
    assert "test prompt for the research agent" not in llm.prompts[0]


def test_exact_count_stable_ids_and_llm_ids_ignored() -> None:
    result = generate_tests(requirement_spec(), MockLLM(as_json(valid_cases())), 3)

    assert len(result) == 3
    assert [item.id for item in result] == ["T1", "T2", "T3"]
    assert all(not item.id.startswith("random-") for item in result)


def test_requirement_ids_reference_only_input_requirements() -> None:
    spec = requirement_spec()
    result = generate_tests(spec, MockLLM(as_json(valid_cases())), 3)
    known_ids = {requirement.id for requirement in spec.requirements}

    assert all(set(item.requirement_ids) <= known_ids for item in result)


def test_relevant_categories_are_covered() -> None:
    result = generate_tests(
        requirement_spec(), MockLLM(as_json(valid_cases())), 3
    )
    categories = {item.category for item in result}

    assert "fresh_information" in categories
    assert "citation_heavy" in categories


@pytest.mark.parametrize(
    ("field", "value"),
    [("category", "unsupported"), ("difficulty", "extreme")],
)
def test_invalid_schema_value_is_rejected(field: str, value: str) -> None:
    invalid = valid_cases()
    invalid[0][field] = value
    llm = MockLLM(as_json(invalid), as_json(invalid))

    with pytest.raises(BenchmarkGenerationError, match="valid benchmark"):
        generate_tests(requirement_spec(), llm, 3)

    assert len(llm.prompts) == 2


def test_malformed_output_retries_once() -> None:
    llm = MockLLM("not JSON", as_json(valid_cases()))

    result = generate_tests(requirement_spec(), llm, 3)

    assert len(result) == 3
    assert len(llm.prompts) == 2
    assert "previous benchmark output was invalid" in llm.prompts[1]


def test_repeated_malformed_output_raises_explicit_error() -> None:
    llm = MockLLM("not JSON", "still not JSON")

    with pytest.raises(BenchmarkGenerationError, match="one correction retry"):
        generate_tests(requirement_spec(), llm, 3)

    assert len(llm.prompts) == 2


def test_unknown_requirement_id_is_rejected() -> None:
    invalid = valid_cases()
    invalid[0]["requirement_ids"] = ["R99"]
    llm = MockLLM(as_json(invalid), as_json(invalid))

    with pytest.raises(BenchmarkGenerationError, match="unknown requirement IDs"):
        generate_tests(requirement_spec(), llm, 3)


@pytest.mark.parametrize("num_cases", [0, -1])
def test_non_positive_count_is_rejected_without_llm_call(num_cases: int) -> None:
    llm = MockLLM()

    with pytest.raises(ValueError, match="greater than 0"):
        generate_tests(requirement_spec(), llm, num_cases)

    assert llm.prompts == []


def test_empty_requirements_are_rejected_without_llm_call() -> None:
    empty_spec = RequirementSpec(
        task_type="research", task_description="Research a topic", requirements=[]
    )
    llm = MockLLM()

    with pytest.raises(ValueError, match="at least one requirement"):
        generate_tests(empty_spec, llm)

    assert llm.prompts == []


def test_impossible_category_coverage_is_rejected_without_llm_call() -> None:
    llm = MockLLM()

    with pytest.raises(ValueError, match="cannot cover 3 mandatory"):
        generate_tests(three_category_requirement_spec(), llm, num_cases=2)

    assert llm.prompts == []


def test_feasible_category_count_still_generates_benchmark() -> None:
    feasible_cases = valid_cases()
    feasible_cases[2] = case(
        "Produce a structured comparison of three agent evaluation frameworks.",
        "formatting",
        "hard",
        ["R3", "R4"],
    )

    result = generate_tests(
        three_category_requirement_spec(),
        MockLLM(as_json(feasible_cases)),
        num_cases=3,
    )

    assert len(result) == 3
    assert {item.category for item in result} == {
        "fresh_information",
        "citation_heavy",
        "formatting",
    }


def test_wrong_number_of_cases_is_rejected() -> None:
    two_cases = valid_cases()[:2]
    llm = MockLLM(as_json(two_cases), as_json(two_cases))

    with pytest.raises(BenchmarkGenerationError, match="expected exactly 3"):
        generate_tests(requirement_spec(), llm, 3)


def test_duplicate_cases_are_rejected() -> None:
    duplicates = valid_cases()
    duplicates[2]["input"] = duplicates[1]["input"]
    llm = MockLLM(as_json(duplicates), as_json(duplicates))

    with pytest.raises(BenchmarkGenerationError, match="near-identical"):
        generate_tests(requirement_spec(), llm, 3)


def test_missing_relevant_category_is_rejected() -> None:
    missing_freshness = valid_cases()
    missing_freshness[0]["category"] = "normal"
    llm = MockLLM(as_json(missing_freshness), as_json(missing_freshness))

    with pytest.raises(BenchmarkGenerationError, match="missing categories"):
        generate_tests(requirement_spec(), llm, 3)
