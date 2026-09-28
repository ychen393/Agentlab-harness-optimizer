import type { AgentLabSnapshot, Language, RequestAnalysis } from "../types/contracts";

export const DEFAULT_REQUEST =
  "My order was paid on 2026-02-10 for 650 RMB. Which promotion applies, and do I qualify for the gift?";

export function parseRequest(input: string, language: Language): RequestAnalysis {
  const amount = input.match(/(?:for|amount|spend|paid|金额)\s*(?:is|of|为|:)?\s*(\d+)\s*(RMB|元)?/i);
  const date = input.match(/\b\d{4}-\d{2}-\d{2}\b/);
  const lower = input.toLowerCase();
  const intent = /promotion|促销|gift|赠品|qualify|eligib|符合.*资格|资格/.test(lower)
    ? language === "zh" ? "促销资格查询" : "Promotion eligibility"
    : /product|商品|catalog|price/.test(lower)
      ? language === "zh" ? "商品信息查询" : "Product information"
      : null;
  return {
    intent,
    amount: amount ? `${amount[1]} ${amount[2] ?? (language === "zh" ? "元" : "RMB")}` : null,
    paymentDate: date?.[0] ?? null,
    orderType: input.trim() ? (language === "zh" ? "在线订单" : "Online order") : null,
  };
}

export function mockAgentLab(): AgentLabSnapshot {
  return {
    trace: {
      test_id: "CT6",
      agent_version: "commerce-v1",
      output: JSON.stringify({ tool: "search_policy", result: "POLICY_B" }),
      tool_calls: ["search_policy"],
      error: "workflow.max_steps = 2; check_eligibility was not reached",
      latency_seconds: 2.3,
    },
    evaluation: {
      test_id: "CT6",
      agent_version: "commerce-v1",
      passed: false,
      final_score: 0.5,
      rule_scores: { required_tool_called: 1, correct_tool_sequence: 0, execution_succeeded: 0 },
      explanation: "Task incomplete: the required eligibility decision was not produced.",
    },
    failure: {
      id: "F1",
      category: "workflow_step_limit",
      count: 2,
      affected_test_ids: ["CT6", "CT7"],
      severity: "high",
      summary: "Multi-step workflows are blocked by the configured workflow step limit.",
    },
    rootCause: {
      failure_category: "workflow_step_limit",
      evidence: [
        "search_policy selected the applicable policy and returned POLICY_B.",
        "The required check_eligibility step was never executed.",
        "Execution was blocked by workflow.max_steps = 2.",
      ],
      root_cause: "The configured workflow budget is insufficient for the required multi-step workflow.",
      target_component: "workflow_config",
      confidence: 0.99,
    },
    patch: {
      target_component: "workflow_config",
      old_value: { max_steps: 2 },
      proposed_value: { max_steps: 3 },
      reason: "The observed workflow step-limit failure is supported by repeated traces.",
      supporting_failure_pattern_ids: ["F1"],
      expected_effect: "Allow the required workflow step blocked by the current budget to execute.",
      regression_risk: "An additional step may increase latency or permit unnecessary tool usage.",
    },
    regression: {
      baseline_version: "commerce-v1",
      candidate_version: "commerce-v2",
      baseline_pass_count: 5,
      candidate_pass_count: 7,
      baseline_total: 7,
      candidate_total: 7,
      improved_test_ids: ["CT6", "CT7"],
      regressed_test_ids: [],
      decision: "accept",
      explanation: "Candidate improved failed tests with no correctness regressions.",
    },
  };
}
