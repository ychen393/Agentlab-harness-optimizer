"""Phase 13 patchability and harness-sensitive Commerce experiments."""

from collections.abc import Callable, Sequence

from app.debugger import analyze_failures
from app.optimizer import run_optimization_cycle
from app.regression import compare_versions
from app.runner import run_benchmark
from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    OptimizationCycleResult,
    RegressionDecision,
)

from .agent import CommerceAgent
from .domain_models import CommerceScenario
from .evaluator import evaluate_commerce


RouterCall = Callable[[str], str]
ValidationResult = tuple[
    list[ExecutionTrace],
    list[EvaluationResult],
    list[ExecutionTrace],
    list[EvaluationResult],
    RegressionDecision,
]


def assess_deterministic_patchability(
    scenario: CommerceScenario,
    agent_config: AgentConfig,
) -> OptimizationCycleResult:
    """Evaluate one deterministic path and refuse patches to ignored fields."""

    trace = run_benchmark(
        [scenario.test_case], agent_config, CommerceAgent()
    )[0]
    evaluation = evaluate_commerce(scenario, trace)
    patterns = analyze_failures([evaluation], [trace])
    if evaluation.passed:
        return OptimizationCycleResult(
            status="no_failures",
            baseline_config=agent_config.model_copy(deep=True),
            baseline_traces=[trace],
            baseline_evaluations=[evaluation],
            failure_patterns=[],
            message=(
                "Deterministic execution passed; no bounded harness patch is "
                "justified."
            ),
        )

    return OptimizationCycleResult(
        status="patch_unavailable",
        baseline_config=agent_config.model_copy(deep=True),
        baseline_traces=[trace],
        baseline_evaluations=[evaluation],
        failure_patterns=patterns,
        message=(
            "The observed deterministic routing path does not consume "
            "system_prompt, tool descriptions, or context. Its routing failure "
            "is therefore unavailable for a bounded harness patch; changing "
            "workflow_config would not correct tool selection."
        ),
    )


def run_harness_sensitive_cycle(
    scenario: CommerceScenario,
    baseline_config: AgentConfig,
    router: RouterCall,
    *,
    candidate_version: str,
) -> OptimizationCycleResult:
    """Run baseline and candidate through the same injected routing mechanism."""

    agent = CommerceAgent(llm=router)
    return run_optimization_cycle(
        [scenario],
        baseline_config,
        agent,
        evaluate_commerce,
        candidate_version=candidate_version,
    )


def validate_harness_candidate(
    fixed_regression: Sequence[CommerceScenario],
    adaptive_challenges: Sequence[CommerceScenario],
    exploratory_challenges: Sequence[CommerceScenario],
    baseline_config: AgentConfig,
    candidate_config: AgentConfig,
    router: RouterCall,
) -> ValidationResult:
    """Rerun all three immutable Commerce suites using one router instance."""

    suites = (
        tuple(fixed_regression),
        tuple(adaptive_challenges),
        tuple(exploratory_challenges),
    )
    if any(not suite for suite in suites):
        raise ValueError("All Commerce validation suites must be non-empty")
    scenarios = tuple(item for suite in suites for item in suite)
    test_ids = [scenario.test_case.id for scenario in scenarios]
    if len(test_ids) != len(set(test_ids)):
        raise ValueError("Commerce validation suites contain duplicate test IDs")

    agent = CommerceAgent(llm=router)
    baseline_traces = run_benchmark(
        [scenario.test_case for scenario in scenarios], baseline_config, agent
    )
    baseline_evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(scenarios, baseline_traces, strict=True)
    ]
    candidate_traces = run_benchmark(
        [scenario.test_case for scenario in scenarios], candidate_config, agent
    )
    candidate_evaluations = [
        evaluate_commerce(scenario, trace)
        for scenario, trace in zip(scenarios, candidate_traces, strict=True)
    ]
    decision = compare_versions(
        baseline_evaluations,
        candidate_evaluations,
        baseline_traces=baseline_traces,
        candidate_traces=candidate_traces,
    )
    return (
        baseline_traces,
        baseline_evaluations,
        candidate_traces,
        candidate_evaluations,
        decision,
    )
