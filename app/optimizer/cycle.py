"""One explicit orchestration path through the AgentLab optimization loop."""

from collections.abc import Callable, Sequence
from typing import Protocol

from app.debugger import analyze_failures, analyze_root_cause
from app.optimizer.harness_patch import propose_harness_patch
from app.optimizer.patcher import apply_harness_patch
from app.regression import compare_versions
from app.runner import TargetAgent, run_benchmark
from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    OptimizationCycleResult,
    TestCase,
)


class BenchmarkItem(Protocol):
    """Minimum benchmark-item surface required by the orchestrator."""

    @property
    def test_case(self) -> TestCase:
        ...


Evaluator = Callable[[BenchmarkItem, ExecutionTrace], EvaluationResult]


def run_optimization_cycle(
    benchmark: Sequence[BenchmarkItem],
    baseline_config: AgentConfig,
    target_agent: TargetAgent,
    evaluator: Evaluator,
    *,
    candidate_version: str,
) -> OptimizationCycleResult:
    """Run one bounded optimization cycle over the same benchmark items."""

    benchmark_items = tuple(benchmark)
    if not benchmark_items:
        raise ValueError("benchmark must contain at least one item")

    baseline_traces, baseline_evaluations = _execute_and_evaluate(
        benchmark_items, baseline_config, target_agent, evaluator
    )
    failure_patterns = analyze_failures(baseline_evaluations, baseline_traces)
    if not failure_patterns:
        return _result(
            status="no_failures",
            baseline_config=baseline_config,
            baseline_traces=baseline_traces,
            baseline_evaluations=baseline_evaluations,
            failure_patterns=[],
            message="Baseline has no failed evaluations; no optimization was necessary.",
        )

    if len(failure_patterns) != 1:
        return _result(
            status="patch_unavailable",
            baseline_config=baseline_config,
            baseline_traces=baseline_traces,
            baseline_evaluations=baseline_evaluations,
            failure_patterns=failure_patterns,
            message=(
                "This MVP cycle can apply one bounded patch, but the baseline "
                f"produced {len(failure_patterns)} failure patterns."
            ),
        )

    failure_pattern = failure_patterns[0]
    root_causes = []
    try:
        root_cause = analyze_root_cause(
            failure_pattern, baseline_traces, baseline_config
        )
        root_causes.append(root_cause)
        patch = propose_harness_patch(
            failure_pattern, root_cause, baseline_config
        )
        candidate_config = apply_harness_patch(
            baseline_config, patch, candidate_version
        )
    except ValueError as error:
        return _result(
            status="patch_unavailable",
            baseline_config=baseline_config,
            baseline_traces=baseline_traces,
            baseline_evaluations=baseline_evaluations,
            failure_patterns=failure_patterns,
            root_cause_analyses=root_causes,
            message=f"No valid bounded patch was produced: {error}",
        )

    candidate_traces, candidate_evaluations = _execute_and_evaluate(
        benchmark_items, candidate_config, target_agent, evaluator
    )
    regression_decision = compare_versions(
        baseline_evaluations,
        candidate_evaluations,
        baseline_traces=baseline_traces,
        candidate_traces=candidate_traces,
    )
    return _result(
        status="completed",
        baseline_config=baseline_config,
        baseline_traces=baseline_traces,
        baseline_evaluations=baseline_evaluations,
        failure_patterns=failure_patterns,
        root_cause_analyses=root_causes,
        proposed_patch=patch,
        candidate_config=candidate_config,
        candidate_traces=candidate_traces,
        candidate_evaluations=candidate_evaluations,
        regression_decision=regression_decision,
        message=(
            "Optimization cycle completed with regression decision "
            f"{regression_decision.decision!r}."
        ),
    )


def _execute_and_evaluate(
    benchmark: tuple[BenchmarkItem, ...],
    agent_config: AgentConfig,
    target_agent: TargetAgent,
    evaluator: Evaluator,
) -> tuple[list[ExecutionTrace], list[EvaluationResult]]:
    traces = run_benchmark(
        [item.test_case for item in benchmark], agent_config, target_agent
    )
    evaluations = [
        evaluator(item, trace)
        for item, trace in zip(benchmark, traces, strict=True)
    ]
    return traces, evaluations


def _result(**values: object) -> OptimizationCycleResult:
    """Validate a result after defensively copying all nested models."""

    result = OptimizationCycleResult.model_validate(values)
    return result.model_copy(deep=True)
