"""Convert natural-language requirements into validated schema objects."""

import json
from collections.abc import Callable

from pydantic import ValidationError

from app.schemas.requirement import Requirement, RequirementSpec


LLMCall = Callable[[str], str]

_ALLOWED_TYPES = (
    "freshness, citation, factuality, coverage, format, tool_usage, other"
)


class RequirementParseError(ValueError):
    """Raised when requirement extraction cannot produce a valid contract."""


def parse_requirement(raw_text: str, llm_call: LLMCall) -> RequirementSpec:
    """Extract a validated requirement specification from natural language.

    The provider-neutral ``llm_call`` receives a prompt and must return JSON text.
    Invalid JSON or schema output is retried once with a correction prompt.
    """

    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("raw_text must be a non-empty string")

    raw_text = raw_text.strip()
    prompt = _build_extraction_prompt(raw_text)
    last_error: ValueError | ValidationError | TypeError | None = None

    for attempt in range(2):
        response = _call_llm(llm_call, prompt)
        try:
            specification = RequirementSpec.model_validate_json(response)
            if not specification.requirements:
                raise ValueError("requirements must contain at least one item")
            return _canonicalize(specification, raw_text)
        except (ValidationError, ValueError, TypeError) as error:
            last_error = error
            if attempt == 0:
                prompt = _build_correction_prompt(raw_text, response, error)

    raise RequirementParseError(
        "LLM output did not match RequirementSpec after one correction retry: "
        f"{last_error}"
    ) from last_error


def _call_llm(llm_call: LLMCall, prompt: str) -> str:
    try:
        response = llm_call(prompt)
    except Exception as error:
        raise RequirementParseError(f"Requirement extraction call failed: {error}") from error

    if not isinstance(response, str):
        raise RequirementParseError("Requirement extraction call must return JSON text")
    return response


def _canonicalize(
    specification: RequirementSpec, raw_text: str
) -> RequirementSpec:
    """Apply deterministic IDs while preserving extracted requirement content."""

    requirements = [
        Requirement(
            id=f"R{index}",
            description=requirement.description,
            type=requirement.type,
            weight=requirement.weight,
        )
        for index, requirement in enumerate(specification.requirements, start=1)
    ]
    return RequirementSpec(
        task_type=specification.task_type,
        task_description=raw_text,
        requirements=requirements,
    )


def _build_extraction_prompt(raw_text: str) -> str:
    raw_text_json = json.dumps(raw_text, ensure_ascii=False)
    return f"""Extract the user's requirements into one RequirementSpec JSON object.

Return JSON only, with exactly these fields:
{{
  "task_type": "string",
  "task_description": "string",
  "requirements": [
    {{
      "id": "R1",
      "description": "criterion supported by the input",
      "type": "one allowed value",
      "weight": 0.0
    }}
  ]
}}

Allowed requirement types: {_ALLOWED_TYPES}.
Use sequential IDs R1, R2, and so on.
Assign each weight between 0 and 1; weights should sum approximately to 1.
Include only requirements supported by the user's text.
Do not invent thresholds, formats, tools, or acceptance criteria.
When wording is ambiguous, preserve that ambiguity in the description.
Do not include markdown fences or commentary.

User input: {raw_text_json}
"""


def _build_correction_prompt(
    raw_text: str, response: str, error: Exception
) -> str:
    return f"""The previous extraction was invalid.
Return a corrected RequirementSpec as JSON only. Do not add requirements that are
not supported by the original user input. Use only these requirement types:
{_ALLOWED_TYPES}.

Original user input: {json.dumps(raw_text, ensure_ascii=False)}
Previous output: {json.dumps(response, ensure_ascii=False)}
Validation error: {error}
"""
