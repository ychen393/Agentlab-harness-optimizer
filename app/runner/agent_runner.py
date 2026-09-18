"""Generic execution boundary between AgentLab Core and Target Agents."""

from typing import Protocol
from time import perf_counter

from app.schemas import AgentConfig, ExecutionTrace, TestCase


class TargetAgent(Protocol):
    """Stable interface required from a Target Agent implementation."""

    def run(
        self, test_case: TestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        """Execute one test case using one harness configuration."""
        ...


def run_agent(
    test_case: TestCase,
    agent_config: AgentConfig,
    target_agent: TargetAgent,
) -> ExecutionTrace:
    """Execute one Target Agent case and contain execution failures."""

    started_at = perf_counter()
    try:
        trace = target_agent.run(
            test_case.model_copy(deep=True),
            agent_config.model_copy(deep=True),
        )
        if not isinstance(trace, ExecutionTrace):
            raise TypeError("target_agent.run() must return ExecutionTrace")

        updates: dict[str, object] = {
            "test_id": test_case.id,
            "agent_version": agent_config.version,
        }
        if trace.latency_seconds is None:
            updates["latency_seconds"] = perf_counter() - started_at
        return trace.model_copy(update=updates)
    except Exception as error:
        return ExecutionTrace(
            test_id=test_case.id,
            agent_version=agent_config.version,
            output="",
            latency_seconds=perf_counter() - started_at,
            error=f"{type(error).__name__}: {error}",
        )


def run_benchmark(
    test_cases: list[TestCase],
    agent_config: AgentConfig,
    target_agent: TargetAgent,
) -> list[ExecutionTrace]:
    """Run cases sequentially; one failed execution does not stop later cases."""

    return [
        run_agent(test_case, agent_config, target_agent)
        for test_case in test_cases
    ]
