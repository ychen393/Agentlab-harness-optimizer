from pydantic import ValidationError

from api.main import DiagnoseRequest, PatchRequest, RegressionRequest, RunRequest, benchmarks, diagnose, failures, patch, patches, regression, regressions, run, runs, tool_contract_demo
from app.targets.commerce.scenarios import COMMERCE_SCENARIOS


def test_run_returns_real_execution_trace() -> None:
    body = run(
        RunRequest(
            request="My order was paid on 2026-02-10 for 650 RMB. Which promotion applies, and do I qualify for the gift?",
            scenario_id="CS6",
        )
    )
    assert body["test_id"].startswith("API-")
    assert body["agent_version"] == "commerce-v1"
    assert body["tool_calls"] == ["search_policy"]
    assert body["tool_call_arguments"] == [{"active_on": "2026-02-10"}]
    assert body["tool_events"][0]["tool_name"] == "search_policy"
    assert body["tool_events"][0]["result"][0]["id"] == "POLICY_B"
    assert body["error"] is not None
    assert body["evaluation_available"] is True
    assert body["evaluation"]["passed"] is False
    assert body["latency_seconds"] >= 0

    diagnosis = diagnose(DiagnoseRequest(run_id=body["run_id"]))
    assert diagnosis["status"] == "diagnosed"
    assert diagnosis["evaluation"]["passed"] is False
    assert diagnosis["failure_pattern"]["category"] == "workflow_step_limit"
    assert diagnosis["failure_pattern"]["affected_test_ids"] == [body["test_id"]]
    assert diagnosis["root_cause"]["target_component"] == "workflow_config"


def test_run_rejects_empty_request() -> None:
    try:
        RunRequest(request="")
    except ValidationError as error:
        assert "String should have at least 1 character" in str(error)
    else:
        raise AssertionError("empty requests must be rejected")


def test_custom_run_is_runnable_but_not_evaluable() -> None:
    body = run(RunRequest(request="Find running shoes"))
    assert body["evaluation_available"] is False
    diagnosis = diagnose(DiagnoseRequest(run_id=body["run_id"]))
    assert diagnosis["status"] == "evaluation_unavailable"
    assert "no registered evaluation reference" in diagnosis["message"]


def test_chinese_promotion_request_uses_registered_workflow_path() -> None:
    body = run(
        RunRequest(
            request="我的订单于 2026-02-10 支付，金额为 650 元。请问适用哪个促销活动？我是否符合赠品领取条件？",
            scenario_id="CS6",
        )
    )

    assert body["tool_calls"] == ["search_policy"]
    assert body["tool_call_arguments"] == [{"active_on": "2026-02-10"}]
    assert body["evaluation"]["passed"] is False


def test_registered_successful_run_returns_evaluation_without_failure_diagnosis() -> None:
    scenario = next(scenario for scenario in COMMERCE_SCENARIOS if scenario.id == "CS2")
    body = run(RunRequest(request=scenario.test_case.input, scenario_id=scenario.id))
    assert body["evaluation_available"] is True
    diagnosis = diagnose(DiagnoseRequest(run_id=body["run_id"]))
    assert diagnosis["status"] == "no_failure"
    assert diagnosis["evaluation"]["passed"] is True
    assert diagnosis["failure_pattern"] is None
    assert diagnosis["root_cause"] is None


def test_benchmarks_expose_real_scenario_and_test_case_data() -> None:
    payload = benchmarks()
    ct6 = next(item for item in payload["fixed_regression"] if item["test_case"]["id"] == "CT6")
    assert ct6["scenario_id"] == "CS6"
    assert "Which promotion applies" in ct6["test_case"]["input"]
    assert ct6["ground_truth"]["expected_tool_calls"] == ["search_policy", "check_eligibility"]
    assert {item["test_case"]["id"] for item in payload["adaptive_challenges"]} == {"AT1", "AT2", "AT3", "AT4", "AT5"}
    assert {item["test_case"]["id"] for item in payload["coverage_exploration"]} == {"EXT1", "EXT2", "EXT3", "EXT4"}


def test_patch_endpoint_returns_real_bounded_workflow_patch() -> None:
    body = run(RunRequest(request="My order was paid on 2026-02-10 for 650 RMB. Which promotion applies, and do I qualify for the gift?", scenario_id="CS6"))
    payload = patch(PatchRequest(run_id=body["run_id"]))
    assert payload["status"] == "patch_ready"
    assert payload["patch"]["target_component"] == "workflow_config"
    assert payload["patch"]["old_value"] == {"max_steps": 2}
    assert payload["patch"]["proposed_value"] == {"max_steps": 3}
    assert payload["patch"]["supporting_failure_pattern_ids"]
    assert payload["failure_pattern"]["category"] == "workflow_step_limit"
    assert payload["root_cause"]["target_component"] == "workflow_config"


def test_patch_endpoint_reports_unavailable_without_registered_context() -> None:
    body = run(RunRequest(request="Find running shoes"))
    payload = patch(PatchRequest(run_id=body["run_id"]))
    assert payload["status"] == "patch_unavailable"
    assert payload["patch"] is None


def test_patch_endpoint_reports_unavailable_when_strategy_cannot_propose(monkeypatch) -> None:
    body = run(RunRequest(request="My order was paid on 2026-02-10 for 650 RMB. Which promotion applies, and do I qualify for the gift?", scenario_id="CS6"))
    monkeypatch.setattr("api.main.propose_harness_patch", lambda *_args: (_ for _ in ()).throw(ValueError("unsupported patch")))
    payload = patch(PatchRequest(run_id=body["run_id"]))
    assert payload["status"] == "patch_unavailable"
    assert payload["message"] == "unsupported patch"


def test_regression_endpoint_applies_patch_and_compares_frozen_ct_suite() -> None:
    body = run(RunRequest(request="My order was paid on 2026-02-10 for 650 RMB. Which promotion applies, and do I qualify for the gift?", scenario_id="CS6"))
    patch_payload = patch(PatchRequest(run_id=body["run_id"]))
    result = regression(RegressionRequest(run_id=body["run_id"]))
    assert patch_payload["status"] == "patch_ready"
    assert result["candidate_config"]["workflow"]["max_steps"] == 3
    assert result["baseline_config"]["workflow"]["max_steps"] == 2
    decision = result["regression_decision"]
    assert [item["test_id"] for item in result["baseline_evaluations"]] == [f"CT{i}" for i in range(1, 8)]
    assert [item["test_id"] for item in result["candidate_evaluations"]] == [f"CT{i}" for i in range(1, 8)]
    assert decision["decision"] == "accept"
    assert decision["improved_test_ids"] == ["CT6", "CT7"]
    assert decision["regressed_test_ids"] == []
    assert decision["baseline_pass_count"] == 5
    assert decision["candidate_pass_count"] == 7


def test_regression_endpoint_requires_generated_patch() -> None:
    body = run(RunRequest(request="Find running shoes"))
    try:
        regression(RegressionRequest(run_id=body["run_id"]))
    except Exception as error:
        assert getattr(error, "status_code", None) == 409
    else:
        raise AssertionError("regression must require a server-side generated patch")


def test_session_history_endpoints_expose_real_accumulated_artifacts() -> None:
    body = run(RunRequest(request="My order was paid on 2026-02-10 for 650 RMB. Which promotion applies, and do I qualify for the gift?", scenario_id="CS6"))
    diagnose(DiagnoseRequest(run_id=body["run_id"]))
    patch(PatchRequest(run_id=body["run_id"]))
    regression(RegressionRequest(run_id=body["run_id"]))
    assert any(item["run_id"] == body["run_id"] for item in runs()["runs"])
    assert any(item["run_id"] == body["run_id"] for item in failures()["failures"])
    assert any(item["run_id"] == body["run_id"] for item in patches()["patches"])
    assert any(item["run_id"] == body["run_id"] for item in regressions()["regressions"])



def test_tool_contract_demo_exposes_seed_held_out_control_and_real_decision() -> None:
    payload = tool_contract_demo()

    assert payload["evidence_boundary"] == "provider_independent_controlled_routing_experiment"
    assert payload["seed"]["test_case"]["id"] == "TD1"
    assert payload["seed"]["baseline"]["passed"] is False
    assert payload["seed"]["candidate"]["passed"] is True
    assert payload["seed"]["baseline"]["tool_call_arguments"][0] == {
        "product_name": "Find Running Shoes."
    }
    assert "query" in payload["seed"]["candidate"]["tool_call_arguments"][0]

    assert [item["test_case"]["id"] for item in payload["held_out"]] == [
        "TD2",
        "TD3",
        "TD4",
    ]
    assert all(item["baseline"]["passed"] is False for item in payload["held_out"])
    assert all(item["candidate"]["passed"] is True for item in payload["held_out"])

    assert payload["control"]["test_case"]["id"] == "TD5"
    assert payload["control"]["baseline"]["passed"] is True
    assert payload["control"]["candidate"]["passed"] is True

    assert payload["failure_pattern"]["category"] == "tool_argument_schema_failure"
    assert payload["root_cause"]["target_component"] == "tool_description"
    assert payload["patch"]["target_component"] == "tool_description"
    assert payload["regression_decision"]["improved_test_ids"] == [
        "TD1",
        "TD2",
        "TD3",
        "TD4",
    ]
    assert payload["regression_decision"]["regressed_test_ids"] == []
    assert payload["regression_decision"]["decision"] == "accept"
