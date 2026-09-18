"""Rule-based, semantic, and combined evaluation contracts."""

from typing import Annotated

from pydantic import BaseModel, Field

from .requirement import NonEmptyStr


NormalizedScore = Annotated[float, Field(ge=0.0, le=1.0)]


class RuleCheckResult(BaseModel):
    """Result of one deterministic evaluation check."""

    metric: str
    passed: bool
    score: NormalizedScore
    explanation: str | None = None


class SemanticScore(BaseModel):
    """Normalized dimensions returned by the semantic judge."""

    factuality: NormalizedScore
    coverage: NormalizedScore
    relevance: NormalizedScore
    evidence_support: NormalizedScore
    reasoning: str


class EvaluationResult(BaseModel):
    """Final structured evaluation for a test execution."""

    test_id: NonEmptyStr
    agent_version: NonEmptyStr
    passed: bool
    final_score: NormalizedScore
    rule_scores: dict[str, NormalizedScore]
    semantic_scores: dict[str, NormalizedScore]
    failed_requirement_ids: list[str]
    explanation: str
