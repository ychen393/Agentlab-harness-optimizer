import type { ExecutionTrace } from "../types/contracts";
import type { EvaluationResult, FailurePattern, RootCauseAnalysis } from "../types/contracts";

const API_BASE_URL = process.env.NEXT_PUBLIC_AGENTLAB_API_URL ?? "http://localhost:8001";

export interface RunResponse extends ExecutionTrace {
  run_id: string;
  evaluation_available: boolean;
  evaluation_context: string | null;
}

export interface DiagnosisResponse {
  status: "diagnosed" | "no_failure" | "evaluation_unavailable";
  evaluation_available: boolean;
  message?: string;
  evaluation: EvaluationResult | null;
  failure_pattern: FailurePattern | null;
  root_cause: RootCauseAnalysis | null;
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
