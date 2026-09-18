"""Generate validated, traceable benchmark test cases."""

import json
import re
from collections.abc import Callable
from difflib import SequenceMatcher

from pydantic import TypeAdapter, ValidationError

from app.schemas.benchmark import TestCase
from app.schemas.requirement import RequirementSpec


LLMCall = Callable[[str], str]

_TEST_CASES_ADAPTER = TypeAdapter(list[TestCase])
_ALLOWED_CATEGORIES = (
    "normal, boundary, adversarial, missing_context, fresh_information, "
    "citation_heavy, tool_required, formatting"
)
_ALLOWED_DIFFICULTIES = "easy, medium, hard"
_REQUIRED_CATEGORY_BY_TYPE = {
    "freshness": "fresh_information",
    "citation": "citation_heavy",
    "format": "formatting",
}
_NEAR_DUPLICATE_THRESHOLD = 0.9


class BenchmarkGenerationError(ValueError):
    """Raised when a valid benchmark cannot be generated after one retry."""


def generate_tests(
    requirement_spec: RequirementSpec,
    llm: LLMCall,
    num_cases: int = 5,
) -> list[TestCase]:
    """Generate exactly ``num_cases`` validated and traceable test cases."""

    if num_cases <= 0:
        raise ValueError("num_cases must be greater than 0")
    if not requirement_spec.requirements:
        raise ValueError("requirement_spec must contain at least one requirement")
    _validate_category_feasibility(requirement_spec, num_cases)

    prompt = _build_generation_prompt(requirement_spec, num_cases)
    last_error: Exception | None = None

    for attempt in range(2):
        response = _call_llm(llm, prompt)
        try:
            candidates = _TEST_CASES_ADAPTER.validate_json(response)
            _validate_candidates(candidates, requirement_spec, num_cases)
            return _assign_stable_ids(candidates)
        except (ValidationError, ValueError, TypeError) as error:
            last_error = error
            if attempt == 0:
                prompt = _build_correction_prompt(
                    requirement_spec, num_cases, response, error
                )

    raise BenchmarkGenerationError(
        "LLM output did not produce a valid benchmark after one correction retry: "
        f"{last_error}"
    ) from last_error


def _call_llm(llm: LLMCall, prompt: str) -> str:
    try:
        response = llm(prompt)
    except Exception as error:
        raise BenchmarkGenerationError(f"Benchmark generation call failed: {error}") from error

    if not isinstance(response, str):
        raise BenchmarkGenerationError("Benchmark generation call must return JSON text")
    return response


def _validate_candidates(
    candidates: list[TestCase],
    requirement_spec: RequirementSpec,
    num_cases: int,
) -> None:
    if len(candidates) != num_cases:
        raise ValueError(
            f"expected exactly {num_cases} test cases, received {len(candidates)}"
        )

    known_ids = {requirement.id for requirement in requirement_spec.requirements}
    for candidate in candidates:
        unknown_ids = set(candidate.requirement_ids) - known_ids
        if unknown_ids:
            raise ValueError(
                f"test case references unknown requirement IDs: {sorted(unknown_ids)}"
            )

    _validate_relevant_category_coverage(candidates, requirement_spec)
    _validate_diversity(candidates)


def _validate_relevant_category_coverage(
    candidates: list[TestCase], requirement_spec: RequirementSpec
) -> None:
    categories = {candidate.category for candidate in candidates}
    required_categories = _required_categories(requirement_spec)
    missing_categories = required_categories - categories
    if missing_categories:
        raise ValueError(
            "benchmark is missing categories required by the specification: "
            f"{sorted(missing_categories)}"
        )


def _required_categories(requirement_spec: RequirementSpec) -> set[str]:
    return {
        _REQUIRED_CATEGORY_BY_TYPE[requirement.type]
        for requirement in requirement_spec.requirements
        if requirement.type in _REQUIRED_CATEGORY_BY_TYPE
    }


def _validate_category_feasibility(
    requirement_spec: RequirementSpec, num_cases: int
) -> None:
    required_categories = _required_categories(requirement_spec)
    if len(required_categories) > num_cases:
        raise ValueError(
            f"num_cases={num_cases} cannot cover {len(required_categories)} mandatory "
            f"benchmark categories: {sorted(required_categories)}"
        )


def _validate_diversity(candidates: list[TestCase]) -> None:
    normalized_inputs = [_normalize_input(candidate.input) for candidate in candidates]
    for index, current in enumerate(normalized_inputs):
        for previous in normalized_inputs[:index]:
            if current == previous or SequenceMatcher(None, previous, current).ratio() >= (
                _NEAR_DUPLICATE_THRESHOLD
            ):
                raise ValueError("benchmark contains duplicate or near-identical test cases")


def _normalize_input(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _assign_stable_ids(candidates: list[TestCase]) -> list[TestCase]:
    return [
        candidate.model_copy(update={"id": f"T{index}"})
        for index, candidate in enumerate(candidates, start=1)
    ]


def _build_generation_prompt(
    requirement_spec: RequirementSpec, num_cases: int
) -> str:
    return f"""Generate exactly {num_cases} diverse benchmark test scenarios for the
provided RequirementSpec. Return a JSON array only; do not use markdown fences.

Each array item must contain exactly:
{{
  "id": "any non-empty placeholder",
  "input": "the test prompt for the Target Agent",
  "category": "one allowed category",
  "difficulty": "one allowed difficulty",
  "requirement_ids": ["one or more existing requirement IDs"]
}}

Allowed categories: {_ALLOWED_CATEGORIES}.
Allowed difficulties: {_ALLOWED_DIFFICULTIES}.
Use only requirement IDs present in the supplied RequirementSpec.
Do not invent product requirements or detailed acceptance criteria.
Avoid duplicate and near-duplicate inputs.
Vary difficulty where appropriate rather than defaulting every case to medium.
Choose different testing conditions that are relevant to the requirements.
If freshness is required, include a fresh_information case.
If citations are required, include a citation_heavy case.
If formatting is required, include a formatting case.

RequirementSpec:
{requirement_spec.model_dump_json(indent=2)}
"""


def _build_correction_prompt(
    requirement_spec: RequirementSpec,
    num_cases: int,
    response: str,
    error: Exception,
) -> str:
    return f"""The previous benchmark output was invalid.
Return a corrected JSON array containing exactly {num_cases} diverse test cases.
Use only these categories: {_ALLOWED_CATEGORIES}.
Use only these difficulties: {_ALLOWED_DIFFICULTIES}.
Every requirement_id must occur in the supplied RequirementSpec.
Do not invent requirements. Do not include markdown or commentary.

RequirementSpec: {requirement_spec.model_dump_json()}
Previous output: {json.dumps(response, ensure_ascii=False)}
Validation error: {error}
"""
