"""Minimal Streamlit evidence viewer for the completed AgentLab MVP loop."""

from app.demo_evidence import (
    DemoEvidence,
    build_demo_evidence,
    evolution_rows,
    validation_rows,
)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="AgentLab Evidence", layout="wide")
    st.title("AgentLab — Harness Evolution Evidence")
    st.caption(
        "Deterministic Commerce evidence and provider-independent mock-router "
        "evidence are labeled separately. External-model behavior is not implied."
    )

    @st.cache_resource
    def evidence() -> DemoEvidence:
        return build_demo_evidence()

    result = evidence()
    _evolution_overview(st, result)
    _failure_root_cause(st, result)
    _patch_diff(st, result)
    _regression_coverage(st, result)


def _evolution_overview(st, evidence: DemoEvidence) -> None:
    st.header("1. Evolution Overview")
    st.dataframe(evolution_rows(evidence), use_container_width=True)
    col1, col2 = st.columns(2)
    col1.info(
        "V1 → V2 · deterministic evidence\n\n"
        "Target: workflow_config\n\nPatch: max_steps 2 → 3"
    )
    col2.info(
        "V2 → V3 · provider-independent mock-router evidence\n\n"
        "Target: system_prompt\n\nPatch: negated-intent routing instruction"
    )
    st.warning(
        "The V3 result proves behavior for the controlled mock router. It does "
        "not establish universal behavior across external models."
    )


def _failure_root_cause(st, evidence: DemoEvidence) -> None:
    st.header("2. Failure → Root Cause")
    first = evidence.first_cycle
    second = evidence.second_cycle
    rows = [
        {
            "evidence_type": "Deterministic execution",
            "test_id": "CT6, CT7",
            "expected": "search_policy → check_eligibility",
            "observed_tools": ", ".join(first.baseline_traces[-2].tool_calls),
            "failure_pattern": first.failure_patterns[0].category,
            "root_cause": first.root_cause_analyses[0].root_cause,
            "confidence": first.root_cause_analyses[0].confidence,
            "target": first.root_cause_analyses[0].target_component,
        },
        {
            "evidence_type": "Provider-independent mock router",
            "test_id": "EXT2",
            "expected": "search_products",
            "observed_tools": ", ".join(second.baseline_traces[0].tool_calls),
            "failure_pattern": second.failure_patterns[0].category,
            "root_cause": second.root_cause_analyses[0].root_cause,
            "confidence": second.root_cause_analyses[0].confidence,
            "target": second.root_cause_analyses[0].target_component,
        },
    ]
    st.dataframe(rows, use_container_width=True)
    st.subheader("Deterministic EX2 patchability gate")
    st.code(evidence.deterministic_patchability.message, language="text")


def _patch_diff(st, evidence: DemoEvidence) -> None:
    st.header("3. Harness Patch Diff")
    first_patch = evidence.first_cycle.proposed_patch
    second_patch = evidence.second_cycle.proposed_patch
    st.subheader("Patch #1 — workflow_config")
    st.code(
        f"workflow.max_steps: {first_patch.old_value['max_steps']} → "
        f"{first_patch.proposed_value['max_steps']}",
        language="diff",
    )
    st.subheader("Patch #2 — system_prompt")
    st.code(
        "- " + second_patch.old_value["system_prompt"] + "\n"
        "+ " + second_patch.proposed_value["system_prompt"],
        language="diff",
    )
    st.caption("No source-code modification occurred in either optimization step.")


def _regression_coverage(st, evidence: DemoEvidence) -> None:
    st.header("4. Regression / Challenge Coverage")
    st.dataframe(validation_rows(evidence), use_container_width=True)
    coverage = evidence.coverage_report
    col1, col2 = st.columns(2)
    col1.subheader("Already covered")
    col1.write(coverage.covered_dimensions)
    col2.subheader("Undercovered before EX generation")
    col2.write(coverage.undercovered_dimensions)
    decision = evidence.final_decision
    st.metric(
        "V2 → V3 combined pass rate",
        f"{decision.candidate_pass_rate:.1%}",
        f"{decision.candidate_pass_rate - decision.baseline_pass_rate:+.1%}",
    )
    st.success(
        f"Derived decision: {decision.decision.upper()} — {decision.explanation}"
    )


if __name__ == "__main__":
    main()
