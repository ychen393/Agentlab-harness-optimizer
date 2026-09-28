"""Reusable harness configurations for the Commerce Target Agent."""

from app.schemas import AgentConfig, InstructionConstraint, ToolConfig, WorkflowConfig

from .tools import DEFAULT_TOOL_DESCRIPTIONS


_TOOL_ARGUMENT_SCHEMAS = {
    "search_products": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    "search_policy": {
        "type": "object",
        "properties": {
            "policy_id": {"type": "string"},
            "active_on": {"type": "string"},
        },
        "required": [],
    },
    "check_eligibility": {
        "type": "object",
        "properties": {
            "policy_id": {"type": "string"},
            "purchase_amount": {"type": "integer"},
            "purchase_date": {"type": "string"},
        },
        "required": ["policy_id", "purchase_amount", "purchase_date"],
    },
}


def commerce_v1_config() -> AgentConfig:
    """Return the intentionally step-limited Commerce V1 harness."""

    return AgentConfig(
        version="commerce-v1",
        system_prompt="Route commerce requests carefully.",
        tools=[
            ToolConfig(
                name=name,
                description=description,
                argument_schema=_TOOL_ARGUMENT_SCHEMAS[name],
            )
            for name, description in DEFAULT_TOOL_DESCRIPTIONS.items()
        ],
        instruction_constraints=[
            InstructionConstraint(
                id="commerce-explicit-intent-routing",
                condition="the user explicitly requests product lookup and excludes promotion lookup",
                required_behavior="route according to the explicit product lookup intent",
                forbidden_behavior="select policy lookup solely because promotion-related words appear",
                required_behavior_key="search_products",
                forbidden_behavior_key="search_policy",
                rationale="Explicit exclusions take precedence over incidental keywords.",
                instruction_lead="Honor explicit exclusions and negated intent",
            )
        ],
        context=["Use only local catalogue and policy facts."],
        workflow=WorkflowConfig(max_steps=2),
    )
