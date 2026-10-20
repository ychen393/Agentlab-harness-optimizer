"""P0 proof that one TD1-derived tool-description patch generalizes safely."""

from app.targets.commerce import (
    TOOL_CONTRACT_CASES,
    TOOL_CONTRACT_CONTROL,
    TOOL_CONTRACT_HELDOUT,
    TOOL_CONTRACT_SEED,
    build_tool_contract_repair_proof,
)


def _evaluation_map(items):
    return {item.test_id: item for item in items}


def _trace_map(items):
    return {item.test_id: item for item in items}


def test_td1_alone_derives_tool_description_patch_from_real_contract_evidence() -> None:
    proof = build_tool_contract_repair_proof()

    assert TOOL_CONTRACT_SEED.test_case.id == "TD1"
    assert proof.seed_trace.tool_calls == ["search_products"]
    assert proof.seed_trace.tool_call_arguments == [
        {"product_name": "Find Running Shoes."}
    ]
    assert proof.seed_evaluation.passed is False

    assert proof.failure_pattern.category == "tool_argument_schema_failure"
    assert proof.failure_pattern.affected_test_ids == ["TD1"]
    assert proof.root_cause.target_component == "tool_description"
    assert proof.root_cause.metadata["tool_name"] == "search_products"
    assert proof.root_cause.metadata["missing_required_arguments"] == ["query"]
    assert proof.root_cause.metadata["unexpected_arguments"] == ["product_name"]
    assert proof.root_cause.metadata["argument_contract_exposed_in_description"] is False
    assert "Arguments:" not in proof.root_cause.metadata["current_tool_description"]
    assert "not exposed in the model-facing tool description" in proof.root_cause.root_cause
    assert any(
        line.startswith("registered argument schema:")
        for line in proof.root_cause.evidence
    )

    assert proof.patch.target_component == "tool_description"
    assert proof.patch.old_value["name"] == "search_products"
    assert 'Arguments: {"query":"<string>"}.' in proof.patch.proposed_value["description"]


def test_patch_changes_only_search_products_description_not_registered_contract() -> None:
    proof = build_tool_contract_repair_proof()
    baseline = proof.baseline_config
    candidate = proof.candidate_config

    baseline_tools = {tool.name: tool for tool in baseline.tools}
    candidate_tools = {tool.name: tool for tool in candidate.tools}

    assert candidate.system_prompt == baseline.system_prompt
    assert candidate.context == baseline.context
    assert candidate.workflow == baseline.workflow
    assert candidate.instruction_constraints == baseline.instruction_constraints
    assert candidate_tools["search_products"].argument_schema == baseline_tools["search_products"].argument_schema
    assert candidate_tools["search_products"].description != baseline_tools["search_products"].description
    assert candidate_tools["search_policy"] == baseline_tools["search_policy"]
    assert candidate_tools["check_eligibility"] == baseline_tools["check_eligibility"]


def test_single_seed_patch_repairs_held_out_cases_and_preserves_negative_control() -> None:
    proof = build_tool_contract_repair_proof()
    baseline_eval = _evaluation_map(proof.baseline_evaluations)
    candidate_eval = _evaluation_map(proof.candidate_evaluations)
    baseline_trace = _trace_map(proof.baseline_traces)
    candidate_trace = _trace_map(proof.candidate_traces)

    assert baseline_eval["TD1"].passed is False
    assert candidate_eval["TD1"].passed is True

    assert [scenario.test_case.id for scenario in TOOL_CONTRACT_HELDOUT] == [
        "TD2",
        "TD3",
        "TD4",
    ]
    for test_id in ("TD2", "TD3", "TD4"):
        assert baseline_eval[test_id].passed is False
        assert candidate_eval[test_id].passed is True
        assert "product_name" in baseline_trace[test_id].tool_call_arguments[0]
        assert "query" in candidate_trace[test_id].tool_call_arguments[0]

    control_id = TOOL_CONTRACT_CONTROL.test_case.id
    assert control_id == "TD5"
    assert baseline_eval[control_id].passed is True
    assert candidate_eval[control_id].passed is True
    assert "query" in baseline_trace[control_id].tool_call_arguments[0]


def test_tool_description_candidate_preserves_frozen_ct1_ct7_and_is_accepted() -> None:
    proof = build_tool_contract_repair_proof()
    baseline_eval = _evaluation_map(proof.baseline_evaluations)
    candidate_eval = _evaluation_map(proof.candidate_evaluations)

    for index in range(1, 8):
        test_id = f"CT{index}"
        assert baseline_eval[test_id].passed is True
        assert candidate_eval[test_id].passed is True

    assert proof.regression_decision.improved_test_ids == [
        "TD1",
        "TD2",
        "TD3",
        "TD4",
    ]
    assert proof.regression_decision.regressed_test_ids == []
    assert proof.regression_decision.unchanged_pass_test_ids == [
        "CT1",
        "CT2",
        "CT3",
        "CT4",
        "CT5",
        "CT6",
        "CT7",
        "TD5",
    ]
    assert proof.regression_decision.baseline_pass_count == 8
    assert proof.regression_decision.candidate_pass_count == len(TOOL_CONTRACT_CASES) + 7
    assert proof.regression_decision.decision == "accept"
