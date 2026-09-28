from pydantic import ValidationError

from api.main import DiagnoseRequest, RunRequest, diagnose, run
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


def test_registered_successful_run_returns_evaluation_without_failure_diagnosis() -> None:
    scenario = next(scenario for scenario in COMMERCE_SCENARIOS if scenario.id == "CS2")
    body = run(RunRequest(request=scenario.test_case.input, scenario_id=scenario.id))
    assert body["evaluation_available"] is True
    diagnosis = diagnose(DiagnoseRequest(run_id=body["run_id"]))
    assert diagnosis["status"] == "no_failure"
    assert diagnosis["evaluation"]["passed"] is True
    assert diagnosis["failure_pattern"] is None
    assert diagnosis["root_cause"] is None
