"""Minimal HTTP adapter for real AgentLab Commerce execution."""

import os
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.runner import run_agent, run_benchmark
from app.schemas import TestCase
from app.targets.commerce.agent import CommerceAgent
from app.targets.commerce.config import commerce_v1_config
from app.targets.commerce.evaluator import evaluate_commerce
from app.targets.commerce.scenarios import COMMERCE_SCENARIOS
from app.debugger.failure_classifier import analyze_failures
from app.debugger.root_cause import analyze_root_cause
from app.demo_evidence import build_demo_evidence
from app.optimizer import propose_harness_patch
from app.optimizer import apply_harness_patch
from app.regression import compare_versions
from app.schemas import HarnessPatch


class RunRequest(BaseModel):
    request: str = Field(min_length=1)
    target: Literal["commerce"] = "commerce"
    agent_version: Literal["commerce-v1"] = "commerce-v1"
    scenario_id: str | None = None


class DiagnoseRequest(BaseModel):
    run_id: str = Field(min_length=1)


class PatchRequest(BaseModel):
    run_id: str = Field(min_length=1)


class RegressionRequest(BaseModel):
    run_id: str = Field(min_length=1)


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "AGENTLAB_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [item.strip() for item in raw.split(",") if item.strip()]


app = FastAPI(title="AgentLab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=os.getenv("AGENTLAB_CORS_ORIGIN_REGEX") or None,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

_SCENARIOS = {scenario.id: scenario for scenario in COMMERCE_SCENARIOS}
_RUNS: dict[str, dict[str, object]] = {}


def _serialize_benchmark_scenario(scenario: object, family: str) -> dict[str, object]:
    return {
        "family": family,
        "scenario_id": scenario.id,
        "test_case": scenario.test_case.model_dump(mode="json"),
        "ground_truth": scenario.ground_truth.model_dump(mode="json"),
    }


@app.get("/api/benchmarks")
def benchmarks() -> dict[str, object]:
    """Expose the registered Commerce benchmark evidence for inspection."""

    evidence = build_demo_evidence()
    return {
        "fixed_regression": [
            _serialize_benchmark_scenario(scenario, "fixed_regression")
            for scenario in COMMERCE_SCENARIOS
        ],
        "adaptive_challenges": [
            _serialize_benchmark_scenario(scenario, "adaptive_challenges")
            for scenario in evidence.adaptive_challenges
        ],
        "coverage_exploration": [
            _serialize_benchmark_scenario(scenario, "coverage_exploration")
            for scenario in evidence.coverage_report.generated_challenges
        ],
    }


def _evaluation_unavailable() -> dict[str, object]:
    return {
        "evaluation_available": False,
        "message": (
            "This request can be executed, but no registered evaluation reference "
            "is available for independent correctness evaluation."
        ),
    }


@app.post("/api/run")
def run(request: RunRequest) -> dict[str, object]:
    """Execute one user-provided Commerce request through the real core."""

    if request.target != "commerce":  # defensive if the Literal grows later
        raise HTTPException(status_code=400, detail="unsupported target")

    test_case = TestCase(
        id=f"API-{uuid4().hex[:12]}",
        input=request.request,
        category="normal",
        difficulty="medium",
        requirement_ids=["API_REQUEST"],
    )
    config = commerce_v1_config()
    trace = run_agent(test_case, config, CommerceAgent())
    run_id = f"RUN-{uuid4().hex[:12]}"
    scenario = _SCENARIOS.get(request.scenario_id) if request.scenario_id else None
    evaluation = evaluate_commerce(scenario, trace) if scenario is not None else None
    _RUNS[run_id] = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request": request.request,
        "scenario_id": scenario.id if scenario is not None else None,
        "trace": trace,
        "config": config,
        "scenario": scenario,
    }
    return {
        **trace.model_dump(mode="json"),
        "run_id": run_id,
        "evaluation_available": scenario is not None,
        "evaluation_context": scenario.id if scenario is not None else None,
        "evaluation": evaluation.model_dump(mode="json") if evaluation is not None else None,
    }


@app.post("/api/diagnose")
def diagnose(request: DiagnoseRequest) -> dict[str, object]:
    """Evaluate a registered run and classify its real failure evidence."""

    record = _RUNS.get(request.run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    scenario = record["scenario"]
    if scenario is None:
        return {"status": "evaluation_unavailable", **_evaluation_unavailable()}

    trace = record["trace"]
    config = record["config"]
    evaluation = evaluate_commerce(scenario, trace)
    if evaluation.passed:
        return {
            "status": "no_failure",
            "evaluation_available": True,
            "evaluation": evaluation.model_dump(mode="json"),
            "failure_pattern": None,
            "root_cause": None,
        }

    patterns = analyze_failures([evaluation], [trace], config)
    root_cause = analyze_root_cause(patterns[0], [trace], config) if patterns else None
    record["evaluation"] = evaluation
    record["failure_pattern"] = patterns[0] if patterns else None
    record["root_cause"] = root_cause
    return {
        "status": "diagnosed",
        "evaluation_available": True,
        "evaluation": evaluation.model_dump(mode="json"),
        "failure_pattern": patterns[0].model_dump(mode="json") if patterns else None,
        "root_cause": root_cause.model_dump(mode="json") if root_cause else None,
    }


@app.post("/api/patch")
def patch(request: PatchRequest) -> dict[str, object]:
    """Propose one bounded harness patch from server-side diagnosis evidence."""

    record = _RUNS.get(request.run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    scenario = record["scenario"]
    if scenario is None:
        return {
            "status": "patch_unavailable",
            "message": "No registered evaluation context is available for this run.",
            "patch": None,
            "failure_pattern": None,
            "root_cause": None,
        }

    trace = record["trace"]
    config = record["config"]
    evaluation = evaluate_commerce(scenario, trace)
    if evaluation.passed:
        return {
            "status": "patch_unavailable",
            "message": "The registered evaluation passed; no patch is needed.",
            "patch": None,
            "failure_pattern": None,
            "root_cause": None,
        }
    pattern = record.get("failure_pattern")
    root_cause = record.get("root_cause")
    if pattern is None:
        patterns = analyze_failures([evaluation], [trace], config)
        pattern = patterns[0] if patterns else None
    if pattern is None:
        return {
            "status": "patch_unavailable",
            "message": "No supported failure pattern was identified.",
            "patch": None,
            "failure_pattern": None,
            "root_cause": None,
        }
    if root_cause is None:
        root_cause = analyze_root_cause(pattern, [trace], config)
    record["evaluation"] = evaluation
    record["failure_pattern"] = pattern
    record["root_cause"] = root_cause
    try:
        proposed = propose_harness_patch(pattern, root_cause, config)
    except (ValueError, TypeError) as exc:
        return {
            "status": "patch_unavailable",
            "message": str(exc),
            "patch": None,
            "failure_pattern": pattern.model_dump(mode="json"),
            "root_cause": root_cause.model_dump(mode="json"),
        }
    record["patch"] = proposed
    return {
        "status": "patch_ready",
        "message": "A bounded harness patch is ready for later regression validation.",
        "patch": proposed.model_dump(mode="json"),
        "failure_pattern": pattern.model_dump(mode="json"),
        "root_cause": root_cause.model_dump(mode="json"),
        "evaluation": evaluation.model_dump(mode="json"),
    }


@app.post("/api/regression")
def regression(request: RegressionRequest) -> dict[str, object]:
    """Apply the stored bounded patch and compare the frozen CT1-CT7 suite."""

    record = _RUNS.get(request.run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    patch_value = record.get("patch")
    if not isinstance(patch_value, HarnessPatch):
        raise HTTPException(status_code=409, detail="no generated HarnessPatch for run_id")

    baseline_config = record["config"]
    try:
        candidate_config = apply_harness_patch(
            baseline_config, patch_value, "commerce-v2"
        )
        scenarios = list(COMMERCE_SCENARIOS)
        target_agent = CommerceAgent()
        baseline_traces = run_benchmark(
            [scenario.test_case for scenario in scenarios],
            baseline_config,
            target_agent,
        )
        baseline_evaluations = [
            evaluate_commerce(scenario, trace)
            for scenario, trace in zip(scenarios, baseline_traces, strict=True)
        ]
        candidate_traces = run_benchmark(
            [scenario.test_case for scenario in scenarios],
            candidate_config,
            target_agent,
        )
        candidate_evaluations = [
            evaluate_commerce(scenario, trace)
            for scenario, trace in zip(scenarios, candidate_traces, strict=True)
        ]
        decision = compare_versions(
            baseline_evaluations,
            candidate_evaluations,
            baseline_traces=baseline_traces,
            candidate_traces=candidate_traces,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"regression failed: {exc}") from exc

    record["candidate_config"] = candidate_config
    record["regression_decision"] = decision
    return {
        "status": "completed",
        "patch": patch_value.model_dump(mode="json"),
        "baseline_config": baseline_config.model_dump(mode="json"),
        "candidate_config": candidate_config.model_dump(mode="json"),
        "baseline_traces": [trace.model_dump(mode="json") for trace in baseline_traces],
        "baseline_evaluations": [item.model_dump(mode="json") for item in baseline_evaluations],
        "candidate_traces": [trace.model_dump(mode="json") for trace in candidate_traces],
        "candidate_evaluations": [item.model_dump(mode="json") for item in candidate_evaluations],
        "regression_decision": decision.model_dump(mode="json"),
    }


def _run_summary(record: dict[str, object]) -> dict[str, object]:
    trace = record["trace"]
    evaluation = record.get("evaluation")
    return {
        "run_id": record["run_id"],
        "created_at": record["created_at"],
        "request": record["request"],
        "scenario_id": record.get("scenario_id"),
        "test_id": trace.test_id,
        "agent_version": trace.agent_version,
        "execution_status": "failed" if trace.error else "completed",
        "evaluation_status": (
            "pass" if evaluation is not None and evaluation.passed
            else "fail" if evaluation is not None else "not_evaluated"
        ),
        "trace": trace.model_dump(mode="json"),
        "evaluation": evaluation.model_dump(mode="json") if evaluation is not None else None,
        "failure_pattern": record["failure_pattern"].model_dump(mode="json") if record.get("failure_pattern") else None,
        "root_cause": record["root_cause"].model_dump(mode="json") if record.get("root_cause") else None,
        "patch": record["patch"].model_dump(mode="json") if record.get("patch") else None,
        "regression": record["regression_decision"].model_dump(mode="json") if record.get("regression_decision") else None,
    }


@app.get("/api/runs")
def runs() -> dict[str, object]:
    return {"session_label": "current_session", "runs": [_run_summary(item) for item in _RUNS.values()]}


@app.get("/api/failures")
def failures() -> dict[str, object]:
    return {"session_label": "current_session", "failures": [
        {"run_id": item["run_id"], "failure_pattern": item["failure_pattern"].model_dump(mode="json"), "root_cause": item["root_cause"].model_dump(mode="json")}
        for item in _RUNS.values() if item.get("failure_pattern") is not None and item.get("root_cause") is not None
    ]}


@app.get("/api/patches")
def patches() -> dict[str, object]:
    return {"session_label": "current_session", "patches": [
        {"run_id": item["run_id"], "patch": item["patch"].model_dump(mode="json")}
        for item in _RUNS.values() if item.get("patch") is not None
    ]}


@app.get("/api/regressions")
def regressions() -> dict[str, object]:
    return {"session_label": "current_session", "regressions": [
        {"run_id": item["run_id"], "regression": item["regression_decision"].model_dump(mode="json")}
        for item in _RUNS.values() if item.get("regression_decision") is not None
    ]}
