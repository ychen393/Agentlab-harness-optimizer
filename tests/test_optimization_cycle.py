"""Integration tests for the explicit end-to-end optimization cycle."""

from dataclasses import dataclass

from app.optimizer import run_optimization_cycle
from app.schemas import (
    AgentConfig,
    EvaluationResult,
    ExecutionTrace,
    TestCase as BenchmarkTestCase,
    WorkflowConfig,
)
from app.targets.commerce import (
    COMMERCE_SCENARIOS,
    CommerceAgent,
    commerce_v1_config,
    evaluate_commerce,
)


def test_real_commerce_optimization_cycle_uses_actual_pipeline_results() -> None:
    baseline = commerce_v1_config()
    baseline_snapshot = baseline.model_copy(deep=True)
    scenarios_snapshot = [
        scenario.model_copy(deep=True) for scenario in COMMERCE_SCENARIOS
    ]

    result = run_optimization_cycle(
        COMMERCE_SCENARIOS,
        baseline,
        CommerceAgent(),
        evaluate_commerce,
        candidate_version="commerce-v2",
    )

    baseline_failed_ids = sorted(
        evaluation.test_id
        for evaluation in result.baseline_evaluations
        if not evaluation.passed
    )
    candidate_failed_ids = sorted(
        evaluation.test_id
        for evaluation in result.candidate_evaluations
        if not evaluation.passed
    )
    expected_decision = (
        "reject"
        if result.regression_decision
        and result.regression_decision.regressed_test_ids
        else "accept"
        if result.regression_decision
        and result.regression_decision.improved_test_ids
        else "review"
    )

    assert result.status == "completed"
    assert len(result.baseline_evaluations) == 7
    assert sum(item.passed for item in result.baseline_evaluations) == 5
    assert baseline_failed_ids == ["CT6", "CT7"]
    assert result.failure_patterns[0].affected_test_ids == baseline_failed_ids
    assert result.root_cause_analyses[0].target_component == "workflow_config"
    assert result.proposed_patch is not None
    assert result.proposed_patch.old_value == {"max_steps": 2}
    assert result.proposed_patch.proposed_value == {"max_steps": 3}
    assert result.candidate_config is not None
    assert result.candidate_config.version == "commerce-v2"
    assert result.candidate_config.workflow.max_steps == 3
    assert result.candidate_config.system_prompt == baseline.system_prompt
    assert result.candidate_config.tools == baseline.tools
    assert result.candidate_config.context == baseline.context
    assert result.candidate_config.workflow.require_citation == baseline.workflow.require_citation
    assert len(result.candidate_evaluations) == 7
    assert sum(item.passed for item in result.candidate_evaluations) == 7
    assert candidate_failed_ids == []
    assert result.regression_decision is not None
    assert result.regression_decision.decision == expected_decision
    assert {item.test_id for item in result.baseline_evaluations} == {
        scenario.test_case.id for scenario in COMMERCE_SCENARIOS
    }
    assert {item.test_id for item in result.candidate_evaluations} == {
        scenario.test_case.id for scenario in COMMERCE_SCENARIOS
    }
    assert baseline == baseline_snapshot
    assert list(COMMERCE_SCENARIOS) == scenarios_snapshot


def test_no_failure_baseline_returns_without_inventing_patch() -> None:
    baseline = commerce_v1_config().model_copy(
        update={
            "version": "commerce-clean",
            "workflow": WorkflowConfig(max_steps=3),
        }
    )

    result = run_optimization_cycle(
        COMMERCE_SCENARIOS,
        baseline,
        CommerceAgent(),
        evaluate_commerce,
        candidate_version="unused-version",
    )

    assert result.status == "no_failures"
    assert all(item.passed for item in result.baseline_evaluations)
    assert result.failure_patterns == []
    assert result.root_cause_analyses == []
    assert result.proposed_patch is None
    assert result.candidate_config is None
    assert result.candidate_traces == []
    assert result.candidate_evaluations == []
    assert result.regression_decision is None


@dataclass
class RuleFailureBenchmarkItem:
    test_case: BenchmarkTestCase


class SuccessfulAgent:
    def run(
        self, test_case: BenchmarkTestCase, agent_config: AgentConfig
    ) -> ExecutionTrace:
        return ExecutionTrace(
            test_id=test_case.id,
            agent_version=agent_config.version,
            output="valid execution",
        )


def failing_rule_evaluator(
    item: RuleFailureBenchmarkItem, trace: ExecutionTrace
) -> EvaluationResult:
    return EvaluationResult(
        test_id=trace.test_id,
        agent_version=trace.agent_version,
        passed=False,
        final_score=0.0,
        rule_scores={"valid_json": 0.0},
        semantic_scores={},
        failed_requirement_ids=item.test_case.requirement_ids,
        explanation="Rule failed.",
    )


def test_unsupported_failure_returns_patch_unavailable_without_candidate() -> None:
    item = RuleFailureBenchmarkItem(
        test_case=BenchmarkTestCase(
            id="T_RULE",
            input="Return structured output.",
            category="formatting",
            difficulty="easy",
            requirement_ids=["R_FORMAT"],
        )
    )
    baseline = AgentConfig(
        version="v1",
        system_prompt="Return structured output.",
        tools=[],
        context=[],
        workflow=WorkflowConfig(max_steps=2),
    )

    result = run_optimization_cycle(
        [item],
        baseline,
        SuccessfulAgent(),
        failing_rule_evaluator,
        candidate_version="v2",
    )

    assert result.status == "patch_unavailable"
    assert result.failure_patterns[0].category == "rule_failure"
    assert result.candidate_config is None
    assert result.regression_decision is None
    assert "Unsupported failure category" in result.message
