"""Reusable harness configurations for the Commerce Target Agent."""

from app.schemas import AgentConfig, WorkflowConfig


def commerce_v1_config() -> AgentConfig:
    """Return the intentionally step-limited Commerce V1 harness."""

    return AgentConfig(
        version="commerce-v1",
        system_prompt="Route commerce requests carefully.",
        tools=[],
        context=["Use only local catalogue and policy facts."],
        workflow=WorkflowConfig(max_steps=2),
    )
