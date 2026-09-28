import json

from app.schemas import ExecutionTrace, ToolCallEvent, WorkflowConfig
from app.targets.commerce.agent import CommerceAgent
from app.targets.commerce.config import commerce_v1_config
from app.targets.commerce.scenarios import COMMERCE_SCENARIOS


def test_generic_tool_event_preserves_result_and_trace_error() -> None:
    event = ToolCallEvent(
        tool_name="weather_lookup",
        arguments={"city": "Vancouver"},
        result={"temperature": 12},
    )
    trace = ExecutionTrace(
        test_id="weather-1",
        agent_version="weather-v1",
        output="",
        tool_calls=["weather_lookup"],
        tool_call_arguments=[event.arguments],
        tool_events=[event],
        error="workflow step limit reached",
    )

    assert trace.tool_events[0].result == {"temperature": 12}
    assert trace.error == "workflow step limit reached"
    assert "POLICY" not in trace.model_dump_json()


def test_commerce_preserves_policy_event_when_next_step_is_blocked() -> None:
    trace = CommerceAgent().run(COMMERCE_SCENARIOS[5].test_case, commerce_v1_config())

    assert trace.tool_calls == ["search_policy"]
    assert len(trace.tool_events) == 1
    assert trace.tool_events[0].tool_name == "search_policy"
    assert trace.tool_events[0].arguments == {"active_on": "2026-02-10"}
    assert trace.tool_events[0].result[0]["id"] == "POLICY_B"
    assert trace.error is not None
    assert "max_steps=2" in trace.error
    assert trace.output == ""


def test_successful_agent_output_remains_distinct_from_tool_event_result() -> None:
    config = commerce_v1_config().model_copy(
        update={"workflow": WorkflowConfig(max_steps=3)}
    )
    trace = CommerceAgent().run(COMMERCE_SCENARIOS[5].test_case, config)

    assert trace.error is None
    assert json.loads(trace.output)["tool"] == "check_eligibility"
    assert trace.tool_events[-1].result == json.loads(trace.output)["result"]
