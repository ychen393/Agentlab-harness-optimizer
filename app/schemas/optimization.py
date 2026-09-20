"""Bounded harness optimization contracts."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr
from .agent import AgentConfig
from .debugging import FailurePattern, RootCauseAnalysis
from .evaluation import EvaluationResult
from .execution import ExecutionTrace
from .regression import RegressionDecision


class HarnessPatch(BaseModel):
    """One traceable proposed change to the editable harness surface."""

    target_component: Literal[
        "system_prompt",
        "tool_description",
        "context",
        "workflow_config",
    ]
    old_value: dict[str, Any]
    proposed_value: dict[str, Any]
    reason: NonEmptyStr
    supporting_failure_pattern_ids: list[NonEmptyStr] = Field(min_length=1)
    expected_effect: NonEmptyStr
    regression_risk: NonEmptyStr


class OptimizationCycleResult(BaseModel):
    """Inspectable result of one bounded baseline-to-candidate cycle."""

    status: Literal["completed", "no_failures", "patch_unavailable"]
    baseline_config: AgentConfig
    baseline_traces: list[ExecutionTrace]
    baseline_evaluations: list[EvaluationResult]
    failure_patterns: list[FailurePattern]
    root_cause_analyses: list[RootCauseAnalysis] = Field(default_factory=list)
    proposed_patch: HarnessPatch | None = None
    candidate_config: AgentConfig | None = None
    candidate_traces: list[ExecutionTrace] = Field(default_factory=list)
    candidate_evaluations: list[EvaluationResult] = Field(default_factory=list)
    regression_decision: RegressionDecision | None = None
    message: NonEmptyStr
