// `execution` means the trace completed; `execution_failed` means the trace
// contains an execution error. Both remain in the evaluation stage.
export type WorkflowState = "ready" | "execution" | "execution_failed" | "diagnosed" | "patch_ready" | "validated";
export type Language = "zh" | "en";

export interface RequestAnalysis {
  intent: string | null;
  amount: string | null;
  paymentDate: string | null;
  orderType: string | null;
}

export interface ExecutionTrace {
  test_id: string;
  agent_version: string;
  output: string;
  tool_calls: string[];
  tool_call_arguments?: Record<string, unknown>[];
  tool_events?: ToolCallEvent[];
  error: string | null;
  latency_seconds: number | null;
  evaluation_available?: boolean;
  evaluation_context?: string | null;
  evaluation?: EvaluationResult | null;
}

export interface ToolCallEvent {
  tool_name: string;
  arguments: Record<string, unknown>;
  result: unknown;
  error: string | null;
  latency_seconds: number | null;
}

export interface EvaluationResult {
  test_id: string;
  agent_version: string;
  passed: boolean;
  final_score: number;
  rule_scores: Record<string, number>;
  explanation: string;
}

export interface FailurePattern {
  id: string;
  category: string;
  count: number;
  affected_test_ids: string[];
  severity: "low" | "medium" | "high";
  summary: string;
}

export interface RootCauseAnalysis {
  failure_category: string;
  evidence: string[];
  root_cause: string;
  target_component: "system_prompt" | "tool_description" | "context" | "workflow_config";
  confidence: number;
  metadata?: Record<string, unknown>;
}

export interface HarnessPatch {
  target_component: string;
  old_value: Record<string, unknown>;
  proposed_value: Record<string, unknown>;
  reason: string;
  supporting_failure_pattern_ids: string[];
  expected_effect: string;
  regression_risk: string;
}

export interface RegressionDecision {
  baseline_version: string;
  candidate_version: string;
  baseline_pass_count: number;
  candidate_pass_count: number;
  baseline_total: number;
  candidate_total: number;
  improved_test_ids: string[];
  regressed_test_ids: string[];
  decision: "accept" | "reject" | "review";
  explanation: string;
}

export interface AgentLabSnapshot {
  trace: ExecutionTrace;
  evaluation: EvaluationResult;
  failure: FailurePattern;
  rootCause: RootCauseAnalysis;
  patch: HarnessPatch;
  regression: RegressionDecision;
}
