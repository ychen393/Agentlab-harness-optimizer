"""Generic validation of observed tool arguments against registered metadata."""

from collections.abc import Mapping
from typing import Any

from app.schemas import ToolArgumentValidationResult, ToolConfig


def validate_tool_arguments(
    tool_contract: ToolConfig,
    observed_arguments: Mapping[str, Any],
) -> ToolArgumentValidationResult:
    """Compare argument names with a JSON-schema-like ToolConfig contract."""

    properties, required = argument_contract_parts(tool_contract)
    observed_keys = set(observed_arguments)
    property_keys = set(properties)
    missing = sorted(set(required) - observed_keys)
    unexpected = sorted(observed_keys - property_keys)
    return ToolArgumentValidationResult(
        valid=not missing and not unexpected,
        missing_required_arguments=missing,
        unexpected_arguments=unexpected,
    )


def argument_contract_parts(
    tool_contract: ToolConfig,
) -> tuple[dict[str, Any], list[str]]:
    """Normalize JSON Schema or a small name-to-type mapping contract."""

    schema = tool_contract.argument_schema
    if "properties" in schema:
        properties = schema.get("properties", {})
        required = schema.get("required", [])
    else:
        properties = schema
        required = list(schema)
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise ValueError(
            f"Invalid argument_schema metadata for tool {tool_contract.name!r}"
        )
    return properties, required


def find_tool_contract(
    tools: list[ToolConfig], tool_name: str
) -> ToolConfig | None:
    """Return the registered contract for a selected tool, if one exists."""

    return next(
        (tool for tool in tools if tool.name == tool_name and tool.argument_schema),
        None,
    )
