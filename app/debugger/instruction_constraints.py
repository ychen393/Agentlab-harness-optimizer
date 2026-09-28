"""Generic matching of observed behavior to registered instructions."""

from app.schemas import AgentConfig, ExecutionTrace, InstructionConstraint


def find_instruction_violation(
    trace: ExecutionTrace,
    agent_config: AgentConfig,
) -> tuple[InstructionConstraint, str] | None:
    """Return the first constraint whose forbidden behavior was observed."""

    observed = set(trace.tool_calls)
    for constraint in agent_config.instruction_constraints:
        required_key = constraint.required_behavior_key or constraint.required_behavior
        forbidden_key = constraint.forbidden_behavior_key or constraint.forbidden_behavior
        if (
            forbidden_key in observed
            and required_key not in observed
        ):
            return constraint, forbidden_key
    return None
