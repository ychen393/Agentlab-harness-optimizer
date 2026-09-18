"""Editable target-agent configuration contracts."""

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr


class ToolConfig(BaseModel):
    """A tool exposed to the target agent."""

    name: str
    description: str


class WorkflowConfig(BaseModel):
    """Execution controls explicitly supported by the MVP contract."""

    max_steps: int = Field(default=6, gt=0)
    require_citation: bool = False


class AgentConfig(BaseModel):
    """A versioned configuration for a target agent."""

    version: NonEmptyStr
    system_prompt: str
    tools: list[ToolConfig]
    context: list[str] = Field(default_factory=list)
    workflow: WorkflowConfig
