"""Requirements understood by AgentLab."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Requirement(BaseModel):
    """One weighted evaluation criterion from a task specification."""

    id: NonEmptyStr
    description: str
    type: Literal[
        "freshness",
        "citation",
        "factuality",
        "coverage",
        "format",
        "tool_usage",
        "other",
    ]
    weight: Annotated[float, Field(ge=0.0, le=1.0)]


class RequirementSpec(BaseModel):
    """Structured task description and its evaluation requirements."""

    task_type: str
    task_description: str
    requirements: list[Requirement]
