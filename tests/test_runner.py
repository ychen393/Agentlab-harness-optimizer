"""Tests for the domain-independent Target Agent Runner."""

from app.runner import run_agent, run_benchmark
from app.schemas import (
    AgentConfig,
    ExecutionTrace,
    TestCase as BenchmarkTestCase,
    ToolConfig,
    WorkflowConfig,
)
from app.targets.commerce import COMMERCE_SCENARIOS, CommerceAgent


class MockTargetAgent:
    def run(
        self, test_case: BenchmarkTestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        return ExecutionTrace(
            test_id=test_case.id,
            agent_version=agent_config.version,
            output="mock output",
            tool_calls=["mock_tool"],
            latency_seconds=0.1,
            input_tokens=10,
            output_tokens=5,
        )


class RaisingTargetAgent:
    def run(
        self, test_case: BenchmarkTestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        raise RuntimeError("target execution failed")


class IncorrectIdentityTargetAgent:
    def run(
        self, test_case: BenchmarkTestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        return ExecutionTrace(
            test_id="WRONG_TEST",
            agent_version="wrong-version",
            output="output",
        )


class MutatingTargetAgent:
    def __init__(self) -> None:
        self.received_test_case: BenchmarkTestCase | None = None
        self.received_agent_config: AgentConfig | None = None

    def run(
        self, test_case: BenchmarkTestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        self.received_test_case = test_case
        self.received_agent_config = agent_config
        test_case.input = "mutated input"
        agent_config.context.append("mutated context")
        return ExecutionTrace(
            test_id=test_case.id,
            agent_version=agent_config.version,
            output="output",
        )


class MissingLatencyTargetAgent:
    def run(
        self, test_case: BenchmarkTestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        return ExecutionTrace(
            test_id=test_case.id,
            agent_version=agent_config.version,
            output="output without target latency",
        )


class SelectivelyFailingTargetAgent:
    def __init__(self) -> None:
        self.executed_ids: list[str] = []

    def run(
        self, test_case: BenchmarkTestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        self.executed_ids.append(test_case.id)
        if test_case.id == "T2":
            raise ValueError("case failed")
        return ExecutionTrace(
            test_id=test_case.id,
            agent_version=agent_config.version,
            output=f"output for {test_case.id}",
        )


def benchmark_case(test_id: str = "T1") -> BenchmarkTestCase:
    return BenchmarkTestCase(
        id=test_id,
        input=f"Input for {test_id}",
        category="normal",
        difficulty="easy",
        requirement_ids=["R1"],
    )


def agent_config() -> AgentConfig:
    return AgentConfig(
        version="V1",
        system_prompt="Follow the configured harness.",
        tools=[ToolConfig(name="mock_tool", description="A mock tool.")],
        context=["Original context"],
        workflow=WorkflowConfig(),
    )


def test_successful_execution_returns_execution_trace() -> None:
    trace = run_agent(benchmark_case(), agent_config(), MockTargetAgent())

    assert isinstance(trace, ExecutionTrace)
    assert trace.error is None


def test_runner_preserves_test_id() -> None:
    trace = run_agent(benchmark_case("T9"), agent_config(), IncorrectIdentityTargetAgent())

    assert trace.test_id == "T9"


def test_runner_preserves_agent_version() -> None:
    trace = run_agent(benchmark_case(), agent_config(), IncorrectIdentityTargetAgent())

    assert trace.agent_version == "V1"


def test_runner_preserves_output() -> None:
    trace = run_agent(benchmark_case(), agent_config(), MockTargetAgent())

    assert trace.output == "mock output"


def test_runner_preserves_tool_calls_and_observability() -> None:
    trace = run_agent(benchmark_case(), agent_config(), MockTargetAgent())

    assert trace.tool_calls == ["mock_tool"]
    assert trace.latency_seconds == 0.1
    assert trace.input_tokens == 10
    assert trace.output_tokens == 5


def test_latency_is_non_negative() -> None:
    trace = run_agent(benchmark_case(), agent_config(), MissingLatencyTargetAgent())

    assert trace.latency_seconds is not None
    assert trace.latency_seconds >= 0


def test_existing_target_agent_latency_is_preserved() -> None:
    trace = run_agent(benchmark_case(), agent_config(), MockTargetAgent())

    assert trace.latency_seconds == 0.1


def test_missing_latency_is_measured_by_runner() -> None:
    trace = run_agent(benchmark_case(), agent_config(), MissingLatencyTargetAgent())

    assert trace.latency_seconds is not None
    assert trace.latency_seconds >= 0


def test_execution_exception_returns_error_trace() -> None:
    trace = run_agent(benchmark_case(), agent_config(), RaisingTargetAgent())

    assert trace.test_id == "T1"
    assert trace.agent_version == "V1"
    assert trace.output == ""
    assert trace.tool_calls == []
    assert trace.error == "RuntimeError: target execution failed"
    assert trace.latency_seconds is not None


def test_invalid_target_return_is_contained_as_error() -> None:
    class InvalidTarget:
        def run(self, test_case, agent_config):
            return {"output": "not a trace"}

    trace = run_agent(benchmark_case(), agent_config(), InvalidTarget())

    assert trace.output == ""
    assert trace.error == "TypeError: target_agent.run() must return ExecutionTrace"


def test_commerce_agent_executes_through_generic_runner() -> None:
    scenario = COMMERCE_SCENARIOS[0]
    config = AgentConfig(
        version="commerce-v1",
        system_prompt="Route commerce requests.",
        tools=[],
        context=[],
        workflow=WorkflowConfig(),
    )

    trace = run_agent(scenario.test_case, config, CommerceAgent())

    assert isinstance(trace, ExecutionTrace)
    assert trace.error is None
    assert trace.tool_calls == ["check_eligibility"]


def test_runner_does_not_mutate_test_case() -> None:
    original = benchmark_case()
    snapshot = original.model_copy(deep=True)

    run_agent(original, agent_config(), MutatingTargetAgent())

    assert original == snapshot


def test_runner_does_not_mutate_agent_config() -> None:
    config = agent_config()
    snapshot = config.model_copy(deep=True)

    run_agent(benchmark_case(), config, MutatingTargetAgent())

    assert config == snapshot


def test_target_agent_mutation_attempts_affect_only_deep_copies() -> None:
    original_case = benchmark_case()
    original_config = agent_config()
    target = MutatingTargetAgent()

    run_agent(original_case, original_config, target)

    assert target.received_test_case is not original_case
    assert target.received_agent_config is not original_config
    assert target.received_test_case is not None
    assert target.received_test_case.input == "mutated input"
    assert target.received_agent_config is not None
    assert target.received_agent_config.context == [
        "Original context",
        "mutated context",
    ]
    assert original_case.input == "Input for T1"
    assert original_config.context == ["Original context"]


def test_benchmark_continues_after_one_case_fails() -> None:
    target = SelectivelyFailingTargetAgent()
    cases = [benchmark_case("T1"), benchmark_case("T2"), benchmark_case("T3")]

    traces = run_benchmark(cases, agent_config(), target)

    assert target.executed_ids == ["T1", "T2", "T3"]
    assert [trace.test_id for trace in traces] == ["T1", "T2", "T3"]
    assert traces[0].error is None
    assert traces[1].error == "ValueError: case failed"
    assert traces[2].error is None


def test_benchmark_preserves_input_case_order() -> None:
    cases = [benchmark_case("T3"), benchmark_case("T1"), benchmark_case("T2")]

    traces = run_benchmark(cases, agent_config(), MockTargetAgent())

    assert [trace.test_id for trace in traces] == ["T3", "T1", "T2"]
