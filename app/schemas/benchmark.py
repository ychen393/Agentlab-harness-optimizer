"""Benchmark test-case contracts."""

from typing import Literal

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr


class TestCase(BaseModel):
    """One benchmark input mapped to relevant requirements."""

    id: NonEmptyStr
    input: str
    category: Literal[
        "normal",
        "boundary",
        "adversarial",
        "missing_context",
        "fresh_information",
        "citation_heavy",
        "tool_required",
        "formatting",
    ]
    difficulty: Literal["easy", "medium", "hard"]
    requirement_ids: list[str] = Field(min_length=1)
