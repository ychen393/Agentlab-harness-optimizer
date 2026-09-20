"""Tests for Phase 14 evidence preparation and text formatting."""

from app.demo_evidence import (
    build_demo_evidence,
    evolution_rows,
    format_cli_report,
    validation_rows,
)


def test_demo_evidence_is_built_from_actual_pipeline_results() -> None:
    evidence = build_demo_evidence()

    assert sum(item.passed for item in evidence.first_cycle.baseline_evaluations) == 5
    assert sum(item.passed for item in evidence.first_cycle.candidate_evaluations) == 7
    assert evidence.deterministic_patchability.status == "patch_unavailable"
    assert evidence.second_cycle.baseline_evaluations[0].passed is False
    assert evidence.second_cycle.candidate_evaluations[0].passed is True
    expected_decision = (
        "reject"
        if evidence.final_decision.regressed_test_ids
        else "accept"
        if evidence.final_decision.improved_test_ids
        else "review"
    )
    assert evidence.final_decision.decision == expected_decision


def test_result_helpers_keep_test_sets_separate() -> None:
    evidence = build_demo_evidence()

    rows = validation_rows(evidence)

    assert [row["test_set"] for row in rows] == [
        "Fixed Regression Set (CT1-CT7)",
        "Adaptive Challenge Set (AC1-AC5)",
        "Coverage Exploration Set (EX1-EX4)",
    ]
    assert [row["v2"] for row in rows] == ["7/7", "5/5", "3/4"]
    assert [row["v3"] for row in rows] == ["7/7", "5/5", "4/4"]
    assert len(evolution_rows(evidence)) == 4


def test_cli_report_contains_story_and_claim_boundaries() -> None:
    report = format_cli_report(build_demo_evidence())

    for step in range(1, 13):
        assert f"{step}." in report
    assert "workflow_config" in report
    assert "system_prompt" in report
    assert "patch_unavailable" in report
    assert "provider-independent mock router" in report
    assert "Optional external-model evidence: not run" in report
    assert "universal real-model" not in report
