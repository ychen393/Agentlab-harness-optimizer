"""Structured contracts for deterministic version comparison."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr


NonNegativeFloat = Annotated[float, Field(ge=0.0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
NormalizedRate = Annotated[float, Field(ge=0.0, le=1.0)]


class MetricComparison(BaseModel):
    """One numeric baseline/candidate metric comparison."""

    metric: NonEmptyStr
    v1: float
    v2: float
    delta: float


class OperationalMetrics(BaseModel):
    """Observational trace metrics that do not determine correctness."""

    average_latency_seconds: NonNegativeFloat | None
    total_tool_calls: NonNegativeInt
    average_tool_calls: NonNegativeFloat
    execution_error_count: NonNegativeInt


class RegressionDecision(BaseModel):
    """Deterministic correctness comparison between two harness versions."""

    baseline_version: NonEmptyStr
    candidate_version: NonEmptyStr
    baseline_pass_count: NonNegativeInt
    candidate_pass_count: NonNegativeInt
    baseline_total: NonNegativeInt
    candidate_total: NonNegativeInt
    baseline_pass_rate: NormalizedRate
    candidate_pass_rate: NormalizedRate
    improved_test_ids: list[str]
    regressed_test_ids: list[str]
    unchanged_pass_test_ids: list[str]
    unchanged_fail_test_ids: list[str]
    comparisons: list[MetricComparison]
    primary_metric_improved: bool
    critical_regression_detected: bool
    baseline_metrics: OperationalMetrics | None = None
    candidate_metrics: OperationalMetrics | None = None
    decision: Literal["accept", "reject", "review"]
    explanation: NonEmptyStr
