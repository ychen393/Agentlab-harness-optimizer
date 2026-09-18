"""Minimal observable Commerce Target Agent."""

import json
import re
from collections.abc import Callable
from datetime import date
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from app.schemas import AgentConfig, ExecutionTrace, TestCase

from .domain_models import EligibilityRequest
from .tools import (
    DEFAULT_TOOL_DESCRIPTIONS,
    check_eligibility,
    search_policy,
    search_products,
)


LLMCall = Callable[[str], str]
_KNOWN_TOOLS = frozenset(DEFAULT_TOOL_DESCRIPTIONS)


class CommerceAgent:
    """A small Target Agent with injectable routing and deterministic tools."""

    def __init__(self, llm: LLMCall | None = None) -> None:
        self._llm = llm

    def run(self, test_case: TestCase, agent_config: AgentConfig) -> ExecutionTrace:
        started_at = perf_counter()
        tool_calls: list[str] = []
        output = ""
        error: str | None = None

        try:
            tool_name, arguments = self._route(test_case.input, agent_config)
            result = self._run_tool(
                tool_name, arguments, tool_calls, agent_config.workflow.max_steps
            )

            if tool_name == "search_policy" and _is_eligibility_request(test_case.input):
                policies = result if isinstance(result, list) else []
                if len(policies) != 1:
                    raise ValueError(
                        "policy discovery must identify exactly one applicable policy"
                    )
                eligibility_arguments = _eligibility_arguments(
                    test_case.input, policy_id=policies[0]["id"]
                )
                tool_name = "check_eligibility"
                result = self._run_tool(
                    tool_name,
                    eligibility_arguments,
                    tool_calls,
                    agent_config.workflow.max_steps,
                )

            payload: dict[str, Any] = {"tool": tool_name, "result": result}
            if agent_config.workflow.require_citation:
                payload["sources"] = [f"local_fixture:{tool_name}"]
            output = json.dumps(payload, default=_json_default, sort_keys=True)
        except Exception as exc:
            error = _error_message(exc)
            output = json.dumps({"error": error}, sort_keys=True)

        return ExecutionTrace(
            test_id=test_case.id,
            agent_version=agent_config.version,
            output=output,
            tool_calls=tool_calls,
            latency_seconds=perf_counter() - started_at,
            error=error,
        )

    def _run_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_calls: list[str],
        max_steps: int,
    ) -> Any:
        required_step = len(tool_calls) + 2
        if max_steps < required_step:
            raise ValueError(
                f"workflow.max_steps={max_steps} cannot execute workflow step "
                f"{required_step} for {tool_name}"
            )
        tool_calls.append(tool_name)
        return self._execute(tool_name, arguments)

    def _route(
        self, user_input: str, agent_config: AgentConfig
    ) -> tuple[str, dict[str, Any]]:
        if self._llm is None:
            return _deterministic_route(user_input)

        response = self._llm(_routing_prompt(user_input, agent_config))
        try:
            route = json.loads(response)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("router must return a JSON object") from exc
        if not isinstance(route, dict):
            raise ValueError("router must return a JSON object")
        tool_name = route.get("tool")
        if tool_name not in _KNOWN_TOOLS:
            raise ValueError(f"router selected unknown tool: {tool_name}")
        arguments = route.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("router arguments must be an object")
        return tool_name, arguments

    @staticmethod
    def _execute(tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "search_products":
            products = search_products(str(arguments.get("query", "")))
            return [product.model_dump(mode="json") for product in products]
        if tool_name == "search_policy":
            active_on = arguments.get("active_on")
            policies = search_policy(
                policy_id=arguments.get("policy_id"),
                active_on=date.fromisoformat(active_on) if active_on else None,
            )
            return [policy.model_dump(mode="json") for policy in policies]
        if tool_name == "check_eligibility":
            request = EligibilityRequest.model_validate(arguments)
            return check_eligibility(request).model_dump(mode="json")
        raise ValueError(f"unsupported tool: {tool_name}")


def _routing_prompt(user_input: str, agent_config: AgentConfig) -> str:
    descriptions = dict(DEFAULT_TOOL_DESCRIPTIONS)
    descriptions.update(
        {tool.name: tool.description for tool in agent_config.tools if tool.name in _KNOWN_TOOLS}
    )
    tool_catalogue = "\n".join(
        f"- {name}: {description}" for name, description in descriptions.items()
    )
    context = "\n".join(agent_config.context) or "(none)"
    return f"""{agent_config.system_prompt}

Select the first commerce tool for the user input. For eligibility questions
without a policy ID, select search_policy so the agent can discover the policy
before checking eligibility.
Available tools:
{tool_catalogue}

Harness context:
{context}

Workflow max_steps: {agent_config.workflow.max_steps}
Return JSON only in this form:
{{"tool": "tool_name", "arguments": {{}}}}

User input: {user_input}
"""


def _deterministic_route(user_input: str) -> tuple[str, dict[str, Any]]:
    lowered = user_input.casefold()
    if _is_eligibility_request(user_input):
        policy_match = re.search(r"policy_[a-z]", user_input, re.IGNORECASE)
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", user_input)
        if not policy_match and date_match:
            return "search_policy", {"active_on": date_match.group(0)}
        return "check_eligibility", _eligibility_arguments(user_input)
    if "policy" in lowered or "promotion" in lowered:
        policy_match = re.search(r"policy_[a-z]", user_input, re.IGNORECASE)
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", user_input)
        return "search_policy", {
            "policy_id": policy_match.group(0).upper() if policy_match else None,
            "active_on": date_match.group(0) if date_match else None,
        }
    return "search_products", {"query": user_input}


def _is_eligibility_request(user_input: str) -> bool:
    lowered = user_input.casefold()
    return any(term in lowered for term in ("eligible", "eligibility", "qualify", "gift"))


def _eligibility_arguments(
    user_input: str, policy_id: str | None = None
) -> dict[str, Any]:
    lowered = user_input.casefold()
    policy_match = re.search(r"policy_[a-z]", user_input, re.IGNORECASE)
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", user_input)
    amount_match = re.search(
        r"(?:amount|spend|paid|for)\s*(?:is|of|:)?\s*(\d+)", lowered
    )
    arguments: dict[str, Any] = {}
    resolved_policy_id = policy_id or (
        policy_match.group(0).upper() if policy_match else None
    )
    if resolved_policy_id:
        arguments["policy_id"] = resolved_policy_id
    if date_match:
        arguments["purchase_date"] = date_match.group(0)
    if amount_match:
        arguments["purchase_amount"] = int(amount_match.group(1))
    return arguments


def _json_default(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _error_message(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return f"invalid or missing domain input: {error.errors(include_url=False)}"
    return str(error) or type(error).__name__
