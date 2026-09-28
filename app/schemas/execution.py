"""Agent execution trace contracts."""

from typing import Any, Annotated

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr


class ToolCallEvent(BaseModel):
    """Generic evidence for one tool invocation observed during a run."""

    tool_name: NonEmptyStr
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any | None = None
    error: str | None = None
    latency_seconds: Annotated[float, Field(ge=0.0)] | None = None


class ExecutionTrace(BaseModel):
    """Observable result of running one agent version on one test case."""

    test_id: NonEmptyStr
    agent_version: NonEmptyStr
    output: str
    tool_calls: list[str] = Field(default_factory=list)
    tool_call_arguments: list[dict[str, Any]] = Field(default_factory=list)
    tool_events: list[ToolCallEvent] = Field(default_factory=list)
    latency_seconds: Annotated[float, Field(ge=0.0)] | None = None
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    error: str | None = None
