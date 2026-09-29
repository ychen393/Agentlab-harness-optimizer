"""Minimal HTTP adapter for real AgentLab Commerce execution."""

from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.runner import run_agent
from app.schemas import TestCase
from app.targets.commerce.agent import CommerceAgent
from app.targets.commerce.config import commerce_v1_config
from app.targets.commerce.evaluator import evaluate_commerce
from app.targets.commerce.scenarios import COMMERCE_SCENARIOS
from app.debugger.failure_classifier import analyze_failures
from app.debugger.root_cause import analyze_root_cause
from app.demo_evidence import build_demo_evidence


class RunRequest(BaseModel):
    request: str = Field(min_length=1)
    target: Literal["commerce"] = "commerce"
    agent_version: Literal["commerce-v1"] = "commerce-v1"
    scenario_id: str | None = None


class DiagnoseRequest(BaseModel):
    run_id: str = Field(min_length=1)


app = FastAPI(title="AgentLab API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

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
    _RUNS[run_id] = {"trace": trace, "config": config, "scenario": scenario}
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
    return {
        "status": "diagnosed",
        "evaluation_available": True,
        "evaluation": evaluation.model_dump(mode="json"),
        "failure_pattern": patterns[0].model_dump(mode="json") if patterns else None,
        "root_cause": root_cause.model_dump(mode="json") if root_cause else None,
    }
