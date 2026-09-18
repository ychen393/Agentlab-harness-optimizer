"""Independent deterministic evaluation for Commerce Target Agent traces."""

import json
from typing import Any

from app.schemas import EvaluationResult, ExecutionTrace, RuleCheckResult

from .domain_models import CommerceGroundTruth, CommerceScenario


def evaluate_commerce(
    scenario: CommerceScenario, trace: ExecutionTrace
) -> EvaluationResult:
    """Compare one execution trace with immutable commerce ground truth."""

    checks = _evaluate_rules(scenario.ground_truth, trace)
    passed = all(check.passed for check in checks)
    final_score = sum(check.score for check in checks) / len(checks)
    failed_checks = [check for check in checks if not check.passed]

    return EvaluationResult(
        test_id=trace.test_id,
        agent_version=trace.agent_version,
        passed=passed,
        final_score=final_score,
        rule_scores={check.metric: check.score for check in checks},
        semantic_scores={},
        failed_requirement_ids=(
            [] if passed else list(scenario.test_case.requirement_ids)
        ),
        explanation=(
            "All deterministic commerce checks passed."
            if passed
            else " ".join(
                check.explanation or f"{check.metric} failed."
                for check in failed_checks
            )
        ),
    )


def _evaluate_rules(
    ground_truth: CommerceGroundTruth, trace: ExecutionTrace
) -> list[RuleCheckResult]:
    checks = [
        _result(
            "execution_succeeded",
            trace.error is None,
            "Target execution returned an error." if trace.error else None,
        ),
        _result(
            "required_tool_called",
            ground_truth.expected_tool in trace.tool_calls,
            f"Required tool {ground_truth.expected_tool!r} was not called.",
        ),
    ]

    payload = _parse_payload(trace.output) if trace.error is None else None
    result = payload.get("result") if isinstance(payload, dict) else None
    result = result if isinstance(result, dict) else {}

    if ground_truth.expected_policy_id is not None:
        actual_policy = result.get("policy_id")
        checks.append(
            _result(
                "correct_policy",
                actual_policy == ground_truth.expected_policy_id,
                f"Expected policy {ground_truth.expected_policy_id!r}, got {actual_policy!r}.",
            )
        )

    if ground_truth.expected_eligible is not None:
        actual_eligible = result.get("eligible")
        checks.append(
            _result(
                "correct_eligibility",
                actual_eligible is ground_truth.expected_eligible,
                f"Expected eligibility {ground_truth.expected_eligible!r}, got {actual_eligible!r}.",
            )
        )
        actual_gift = result.get("gift")
        checks.append(
            _result(
                "correct_gift",
                actual_gift == ground_truth.expected_gift,
                f"Expected gift {ground_truth.expected_gift!r}, got {actual_gift!r}.",
            )
        )

    if ground_truth.expected_error:
        checks.append(
            _result(
                "missing_information_detected",
                trace.error is not None,
                "Missing-information scenario did not produce an explicit error.",
            )
        )

    return checks


def _parse_payload(output: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def _result(
    metric: str, passed: bool, failure_explanation: str | None
) -> RuleCheckResult:
    return RuleCheckResult(
        metric=metric,
        passed=passed,
        score=1.0 if passed else 0.0,
        explanation=None if passed else failure_explanation,
    )
