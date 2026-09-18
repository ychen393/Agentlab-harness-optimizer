"""Focused tests for the minimal Commerce Target Agent."""

import json
from datetime import date

from app.schemas import AgentConfig, ExecutionTrace, TestCase as BenchmarkTestCase
from app.schemas import ToolConfig, WorkflowConfig
from app.targets.commerce import COMMERCE_SCENARIOS, CommerceAgent
from app.targets.commerce.domain_models import EligibilityRequest
from app.targets.commerce.policies import POLICIES
from app.targets.commerce.tools import check_eligibility, search_policy, search_products


class MockLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def agent_config(
    *, max_steps: int = 6, require_citation: bool = False
) -> AgentConfig:
    return AgentConfig(
        version="commerce-v1",
        system_prompt="Route commerce requests carefully.",
        tools=[
            ToolConfig(
                name="search_products",
                description="CUSTOM PRODUCT LOOKUP DESCRIPTION",
            )
        ],
        context=["Use only local catalogue and policy facts."],
        workflow=WorkflowConfig(
            max_steps=max_steps, require_citation=require_citation
        ),
    )


def product_test_case() -> BenchmarkTestCase:
    return BenchmarkTestCase(
        id="CT_PRODUCT",
        input="Running Shoes",
        category="normal",
        difficulty="easy",
        requirement_ids=["R_PRODUCT"],
    )


def test_run_interface_preserves_ids_and_returns_trace() -> None:
    trace = CommerceAgent().run(product_test_case(), agent_config())

    assert isinstance(trace, ExecutionTrace)
    assert trace.test_id == "CT_PRODUCT"
    assert trace.agent_version == "commerce-v1"


def test_product_search_tool_executes() -> None:
    products = search_products("running shoes")

    assert [product.id for product in products] == ["P1"]


def test_policy_lookup_tool_executes() -> None:
    policies = search_policy(policy_id="POLICY_A")

    assert [policy.id for policy in policies] == ["POLICY_A"]


def test_eligibility_logic_is_deterministic_and_boundaries_are_inclusive() -> None:
    eligible = check_eligibility(
        EligibilityRequest(
            policy_id="POLICY_A",
            purchase_amount=500,
            purchase_date=date(2026, 1, 31),
        )
    )
    insufficient = check_eligibility(
        EligibilityRequest(
            policy_id="POLICY_B",
            purchase_amount=599,
            purchase_date=date(2026, 2, 10),
        )
    )

    assert eligible.eligible is True
    assert eligible.gift == "Gift A"
    assert insufficient.eligible is False
    assert insufficient.reason == "insufficient_purchase_amount"


def test_tool_calls_are_recorded() -> None:
    trace = CommerceAgent().run(COMMERCE_SCENARIOS[0].test_case, agent_config())

    assert trace.tool_calls == ["check_eligibility"]
    assert trace.error is None


def test_agent_config_prompt_fields_are_used() -> None:
    llm = MockLLM(
        json.dumps({"tool": "search_products", "arguments": {"query": "Running Shoes"}})
    )
    trace = CommerceAgent(llm=llm).run(product_test_case(), agent_config())

    assert trace.error is None
    prompt = llm.prompts[0]
    assert "Route commerce requests carefully." in prompt
    assert "CUSTOM PRODUCT LOOKUP DESCRIPTION" in prompt
    assert "Use only local catalogue and policy facts." in prompt
    assert "Workflow max_steps: 6" in prompt


def test_workflow_config_changes_execution() -> None:
    limited = CommerceAgent().run(product_test_case(), agent_config(max_steps=1))
    cited = CommerceAgent().run(
        product_test_case(), agent_config(require_citation=True)
    )

    assert limited.error is not None
    assert "max_steps" in limited.error
    assert json.loads(cited.output)["sources"] == ["local_fixture:search_products"]


def test_missing_domain_input_returns_explicit_trace_error() -> None:
    trace = CommerceAgent().run(COMMERCE_SCENARIOS[4].test_case, agent_config())

    assert trace.error is not None
    assert "invalid or missing domain input" in trace.error
    assert trace.tool_calls == ["check_eligibility"]


def test_router_failure_is_captured_in_trace() -> None:
    trace = CommerceAgent(llm=MockLLM("not-json")).run(
        product_test_case(), agent_config()
    )

    assert isinstance(trace, ExecutionTrace)
    assert trace.error == "router must return a JSON object"
    assert trace.tool_calls == []


def test_local_policy_fixtures_have_known_outcomes() -> None:
    assert [(policy.id, policy.min_amount, policy.gift) for policy in POLICIES] == [
        ("POLICY_A", 500, "Gift A"),
        ("POLICY_B", 600, "Gift B"),
    ]


def test_deterministic_scenario_executes_with_expected_result() -> None:
    scenario = COMMERCE_SCENARIOS[1]
    trace = CommerceAgent().run(scenario.test_case, agent_config())
    result = json.loads(trace.output)["result"]

    assert trace.error is None
    assert result["policy_id"] == scenario.ground_truth.expected_policy_id
    assert result["eligible"] == scenario.ground_truth.expected_eligible
    assert result["gift"] == scenario.ground_truth.expected_gift


def test_policy_discovery_executes_multi_step_workflow() -> None:
    scenario = COMMERCE_SCENARIOS[5]

    trace = CommerceAgent().run(scenario.test_case, agent_config(max_steps=3))
    result = json.loads(trace.output)["result"]

    assert trace.error is None
    assert trace.tool_calls == ["search_policy", "check_eligibility"]
    assert result == {
        "eligible": True,
        "gift": "Gift B",
        "policy_id": "POLICY_B",
        "reason": "eligible",
    }


def test_max_steps_constrains_policy_discovery_workflow() -> None:
    scenario = COMMERCE_SCENARIOS[5]

    trace = CommerceAgent().run(scenario.test_case, agent_config(max_steps=2))

    assert trace.error is not None
    assert "max_steps=2" in trace.error
    assert trace.tool_calls == ["search_policy"]


def test_injected_route_can_use_harness_to_start_multi_step_workflow() -> None:
    llm = MockLLM(
        json.dumps(
            {"tool": "search_policy", "arguments": {"active_on": "2026-02-10"}}
        )
    )
    scenario = COMMERCE_SCENARIOS[5]

    trace = CommerceAgent(llm=llm).run(
        scenario.test_case, agent_config(max_steps=3)
    )

    assert trace.error is None
    assert trace.tool_calls == ["search_policy", "check_eligibility"]
    assert "CUSTOM PRODUCT LOOKUP DESCRIPTION" in llm.prompts[0]
