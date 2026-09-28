"""Editable target-agent configuration contracts."""

from typing import Any

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr


class ToolConfig(BaseModel):
    """A tool exposed to the target agent."""

    name: str
    description: str
    argument_schema: dict[str, Any] = Field(default_factory=dict)


class ToolArgumentValidationResult(BaseModel):
    """Deterministic comparison of observed arguments with a tool contract."""

    valid: bool
    missing_required_arguments: list[str] = Field(default_factory=list)
    unexpected_arguments: list[str] = Field(default_factory=list)


class InstructionConstraint(BaseModel):
    """A reusable behavioral constraint that a harness prompt must encode."""

    id: NonEmptyStr
    condition: NonEmptyStr
    required_behavior: NonEmptyStr
    forbidden_behavior: NonEmptyStr
    required_behavior_key: NonEmptyStr | None = None
    forbidden_behavior_key: NonEmptyStr | None = None
    rationale: NonEmptyStr | None = None
    instruction_lead: NonEmptyStr = "Instruction constraint"


class WorkflowConfig(BaseModel):
    """Execution controls explicitly supported by the MVP contract."""

    max_steps: int = Field(default=6, gt=0)
    require_citation: bool = False


class AgentConfig(BaseModel):
    """A versioned configuration for a target agent."""

    version: NonEmptyStr
    system_prompt: str
    tools: list[ToolConfig]
    instruction_constraints: list[InstructionConstraint] = Field(default_factory=list)
    context: list[str] = Field(default_factory=list)
    workflow: WorkflowConfig
