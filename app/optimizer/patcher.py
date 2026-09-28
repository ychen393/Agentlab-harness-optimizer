"""Safely apply bounded HarnessPatch objects to new config versions."""

from app.schemas import AgentConfig, HarnessPatch, WorkflowConfig


_ALLOWED_COMPONENTS = {
    "system_prompt",
    "tool_description",
    "context",
    "workflow_config",
}


def apply_harness_patch(
    current_config: AgentConfig,
    patch: HarnessPatch,
    new_version: str,
) -> AgentConfig:
    """Create a new AgentConfig version without mutating either input."""

    if patch.target_component not in _ALLOWED_COMPONENTS:
        raise ValueError(
            f"Patch target component is not editable: {patch.target_component!r}"
        )
    normalized_version = new_version.strip()
    if not normalized_version:
        raise ValueError("new_version must be a non-empty string")
    if normalized_version == current_config.version:
        raise ValueError("new_version must differ from the current config version")
    if not patch.supporting_failure_pattern_ids:
        raise ValueError("HarnessPatch must reference supporting failure patterns")

    if patch.target_component == "system_prompt":
        return _apply_system_prompt_patch(
            current_config, patch, normalized_version
        )
    if patch.target_component == "tool_description":
        return _apply_tool_description_patch(
            current_config, patch, normalized_version
        )
    if patch.target_component != "workflow_config":
        raise ValueError(
            "Patch application is not implemented for target component "
            f"{patch.target_component!r}"
        )

    expected_keys = {"max_steps"}
    if set(patch.old_value) != expected_keys or set(patch.proposed_value) != expected_keys:
        raise ValueError(
            "Workflow patches in this phase may modify only workflow.max_steps"
        )

    current_value = {"max_steps": current_config.workflow.max_steps}
    if patch.old_value != current_value:
        raise ValueError(
            "Stale HarnessPatch: old_value does not match current AgentConfig "
            f"value {current_value!r}"
        )

    proposed_workflow = WorkflowConfig.model_validate(
        {
            **current_config.workflow.model_dump(),
            **patch.proposed_value,
        }
    )
    return current_config.model_copy(
        deep=True,
        update={"version": normalized_version, "workflow": proposed_workflow},
    )


def _apply_system_prompt_patch(
    current_config: AgentConfig,
    patch: HarnessPatch,
    new_version: str,
) -> AgentConfig:
    expected_keys = {"system_prompt"}
    if set(patch.old_value) != expected_keys or set(patch.proposed_value) != expected_keys:
        raise ValueError(
            "System-prompt patches may modify only system_prompt"
        )
    if patch.old_value != {"system_prompt": current_config.system_prompt}:
        raise ValueError(
            "Stale HarnessPatch: old_value does not match current AgentConfig "
            "system_prompt"
        )
    proposed_prompt = patch.proposed_value["system_prompt"]
    if not isinstance(proposed_prompt, str) or not proposed_prompt.strip():
        raise ValueError("Proposed system_prompt must be a non-empty string")
    return current_config.model_copy(
        deep=True,
        update={"version": new_version, "system_prompt": proposed_prompt},
    )


def _apply_tool_description_patch(
    current_config: AgentConfig,
    patch: HarnessPatch,
    new_version: str,
) -> AgentConfig:
    expected_keys = {"name", "description"}
    if (
        set(patch.old_value) != expected_keys
        or set(patch.proposed_value) != expected_keys
    ):
        raise ValueError("Tool-description patches may modify only one tool description")
    tool_name = patch.old_value["name"]
    if tool_name != patch.proposed_value["name"]:
        raise ValueError("Tool-description patch cannot rename a tool")
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise ValueError("Tool-description patch requires a non-empty tool name")
    current_description = _current_tool_description(current_config, tool_name)
    if current_description is not None and patch.old_value.get("description") != current_description:
        raise ValueError("Stale HarnessPatch: tool description does not match AgentConfig")
    proposed_description = patch.proposed_value["description"]
    if not isinstance(proposed_description, str) or not proposed_description.strip():
        raise ValueError("Proposed tool description must be a non-empty string")

    tools = current_config.tools
    replacement = next(
        (tool.model_copy(update={"description": proposed_description})
         for tool in tools if tool.name == tool_name),
        None,
    )
    if replacement is None:
        from app.schemas import ToolConfig

        updated_tools = [*tools, ToolConfig(name=tool_name, description=proposed_description)]
    else:
        updated_tools = [replacement if tool.name == tool_name else tool for tool in tools]
    return current_config.model_copy(
        deep=True,
        update={"version": new_version, "tools": updated_tools},
    )


def _current_tool_description(current_config: AgentConfig, tool_name: str) -> str | None:
    return next(
        (tool.description for tool in current_config.tools if tool.name == tool_name),
        None,
    )
