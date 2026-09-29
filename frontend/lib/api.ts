import type { ExecutionTrace } from "../types/contracts";
import type { EvaluationResult, FailurePattern, RootCauseAnalysis } from "../types/contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_AGENTLAB_API_URL ?? "http://localhost:8001";

export interface RunResponse extends ExecutionTrace {
  run_id: string;
  evaluation_available: boolean;
  evaluation_context: string | null;
  evaluation: EvaluationResult | null;
}

export interface DiagnosisResponse {
  status: "diagnosed" | "no_failure" | "evaluation_unavailable";
  evaluation_available: boolean;
  message?: string;
  evaluation: EvaluationResult | null;
  failure_pattern: FailurePattern | null;
  root_cause: RootCauseAnalysis | null;
}

export interface PatchResponse {
  status: "patch_ready" | "patch_unavailable";
  message?: string;
  patch: import("../types/contracts").HarnessPatch | null;
  failure_pattern: FailurePattern | null;
  root_cause: RootCauseAnalysis | null;
  evaluation?: EvaluationResult | null;
}

export interface RegressionResponse {
  status: "completed";
  patch: import("../types/contracts").HarnessPatch;
  baseline_config: Record<string, unknown>;
  candidate_config: Record<string, unknown>;
  baseline_traces: ExecutionTrace[];
  baseline_evaluations: EvaluationResult[];
  candidate_traces: ExecutionTrace[];
  candidate_evaluations: EvaluationResult[];
  regression_decision: import("../types/contracts").RegressionDecision;
}

export interface SessionRun {
  run_id: string; created_at: string; request: string; scenario_id: string | null;
  test_id: string; agent_version: string; execution_status: string; evaluation_status: string;
  trace: ExecutionTrace; evaluation: EvaluationResult | null;
  failure_pattern: FailurePattern | null; root_cause: RootCauseAnalysis | null;
  patch: import("../types/contracts").HarnessPatch | null;
  regression: import("../types/contracts").RegressionDecision | null;
}

export interface BenchmarkCase {
  family: "fixed_regression" | "adaptive_challenges" | "coverage_exploration";
  scenario_id: string;
  test_case: {
    id: string;
    input: string;
    category: string;
    difficulty: string;
    requirement_ids: string[];
  };
  ground_truth: {
    expected_tool: string;
    expected_tool_calls?: string[] | null;
    expected_policy_id?: string | null;
    expected_eligible?: boolean | null;
    expected_gift?: string | null;
    expected_error?: boolean;
  };
}

export interface BenchmarkResponse {
  fixed_regression: BenchmarkCase[];
  adaptive_challenges: BenchmarkCase[];
  coverage_exploration: BenchmarkCase[];
}

export async function runCommerceRequest(request: string, scenarioId: string | null): Promise<RunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ request, target: "commerce", agent_version: "commerce-v1", scenario_id: scenarioId }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`AgentLab API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<RunResponse>;
}

export async function diagnoseRun(runId: string): Promise<DiagnosisResponse> {
  const response = await fetch(`${API_BASE_URL}/api/diagnose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`AgentLab diagnosis API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<DiagnosisResponse>;
}

export async function generatePatch(runId: string): Promise<PatchResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`AgentLab patch API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<PatchResponse>;
}

export async function runRegression(runId: string): Promise<RegressionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/regression`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`AgentLab regression API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<RegressionResponse>;
}

export async function fetchBenchmarks(): Promise<BenchmarkResponse> {
  const response = await fetch(`${API_BASE_URL}/api/benchmarks`);
  if (!response.ok) throw new Error(`AgentLab benchmark API ${response.status}: ${await response.text()}`);
  return response.json() as Promise<BenchmarkResponse>;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(`AgentLab history API ${response.status}: ${await response.text()}`);
  return response.json() as Promise<T>;
}

export const fetchRuns = () => getJson<{ session_label: string; runs: SessionRun[] }>("/api/runs");
export const fetchFailures = () => getJson<{ session_label: string; failures: Array<{ run_id: string; failure_pattern: FailurePattern; root_cause: RootCauseAnalysis }> }>("/api/failures");
export const fetchPatches = () => getJson<{ session_label: string; patches: Array<{ run_id: string; patch: import("../types/contracts").HarnessPatch }> }>("/api/patches");
export const fetchRegressions = () => getJson<{ session_label: string; regressions: Array<{ run_id: string; regression: import("../types/contracts").RegressionDecision }> }>("/api/regressions");
