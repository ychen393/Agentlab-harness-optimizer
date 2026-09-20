"""Failure-analysis contracts shared by debugger and optimizer modules."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr


class FailurePattern(BaseModel):
    """A recurring, traceable failure observed across benchmark executions."""

    id: NonEmptyStr
    category: str
    count: int
    affected_test_ids: list[str]
    severity: Literal["low", "medium", "high"]
    summary: str


class RootCauseAnalysis(BaseModel):
    """Evidence-backed diagnosis of one observed failure pattern."""

    failure_category: str
    evidence: list[str]
    root_cause: str
    target_component: Literal[
        "system_prompt",
        "tool_description",
        "context",
        "workflow_config",
    ]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
