"""Failure-analysis contracts shared by debugger and optimizer modules."""

from typing import Literal

from pydantic import BaseModel

from .requirement import NonEmptyStr


class FailurePattern(BaseModel):
    """A recurring, traceable failure observed across benchmark executions."""

    id: NonEmptyStr
    category: str
    count: int
    affected_test_ids: list[str]
    severity: Literal["low", "medium", "high"]
    summary: str
