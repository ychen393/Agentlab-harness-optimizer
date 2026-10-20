"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Check, CircleAlert, FlaskConical, ShieldCheck, Wrench } from "lucide-react";
import { RouteShell } from "../../components/route-shell";
import {
  fetchToolContractDemo,
  type ToolContractCaseResult,
  type ToolContractDemoResponse,
} from "../../lib/api";
import type { Language } from "../../types/contracts";

const COPY = {
  zh: {
    title: "工具契约修复实验",
    subtitle: "一次 Seed Failure 生成一个受约束 Patch，再用未见案例、负对照和冻结回归验证它是否真的泛化。",
    badge: "可复现受控路由实验",
    boundary: "不依赖外部模型 API；同一受控 Router 会真实读取 Harness 中的 tool_description。",
    seed: "发现问题",
    seedBody: "仅 TD1 用于生成 FailurePattern、RootCauseAnalysis 和 HarnessPatch。",
    diagnose: "定位根因",
    diagnoseBody: "Agent 选对了 search_products，但参数名违反已注册工具契约。",
    patch: "受约束修复",
    patchBody: "只修改 tool_description，不修改 argument_schema、业务逻辑、Evaluator 或 Ground Truth。",
    validate: "未见案例验证",
    validateBody: "TD2–TD4 不参与 Patch 生成，只用于验证一次修复是否跨请求生效。",
    baseline: "修复前",
    candidate: "修复后",
    actualArg: "实际参数",
    requiredArg: "工具要求",
    failurePattern: "失败模式",
    rootCause: "根因",
    targetSurface: "目标 Harness 面",
    patchDiff: "HarnessPatch",
    before: "修改前",
    after: "修改后",
    matrix: "验证矩阵",
    role: "角色",
    request: "请求",
    result: "结果",
    improved: "改善",
    preserved: "保持通过",
    regressed: "新增回退",
    decision: "最终决策",
    accept: "接受修改",
    seedRole: "Seed · Patch 生成",
    heldoutRole: "Held-out · 未见验证",
    controlRole: "Control · 负对照",
    fixed: "CT1–CT7 冻结回归",
    fixedBody: "原有促销与资格判断能力保持通过。",
    noRegression: "0 个新增正确性回退",
    loading: "正在生成真实证据…",
    error: "无法加载工具契约修复证据",
  },
  en: {
    title: "Tool Contract Repair Experiment",
    subtitle: "One seed failure produces one bounded patch, then held-out cases, a negative control, and frozen regression test whether it generalizes.",
    badge: "Provider-independent controlled routing experiment",
    boundary: "No external model API is required; the same controlled router actually consumes tool_description from the Harness.",
    seed: "Discover failure",
    seedBody: "Only TD1 contributes evidence to FailurePattern, RootCauseAnalysis, and HarnessPatch.",
    diagnose: "Diagnose root cause",
    diagnoseBody: "The Agent selects search_products correctly, but its argument name violates the registered tool contract.",
    patch: "Bounded repair",
    patchBody: "Only tool_description changes; argument_schema, business logic, Evaluator, and Ground Truth remain frozen.",
    validate: "Held-out validation",
    validateBody: "TD2–TD4 do not contribute to patch generation and only test whether the single repair works across requests.",
    baseline: "Baseline",
    candidate: "Candidate",
    actualArg: "Observed argument",
    requiredArg: "Required argument",
    failurePattern: "Failure pattern",
    rootCause: "Root cause",
    targetSurface: "Target Harness surface",
    patchDiff: "HarnessPatch",
    before: "Before",
    after: "After",
    matrix: "Validation matrix",
    role: "Role",
    request: "Request",
    result: "Result",
    improved: "Improved",
    preserved: "Preserved",
    regressed: "Regressions",
    decision: "Final decision",
    accept: "ACCEPT",
    seedRole: "Seed · patch derivation",
    heldoutRole: "Held-out · unseen validation",
    controlRole: "Control · negative control",
    fixed: "CT1–CT7 frozen regression",
    fixedBody: "Existing promotion and eligibility capability remains passing.",
    noRegression: "0 new correctness regressions",
    loading: "Building real evidence…",
    error: "Unable to load tool-contract repair evidence",
  },
} as const;

export default function ToolContractPage() {
  return <RouteShell>{(language) => <ToolContractContent language={language} />}</RouteShell>;
}

function ToolContractContent({ language }: { language: Language }) {
  const c = COPY[language];
  const [data, setData] = useState<ToolContractDemoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchToolContractDemo().then(setData).catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, []);

  const cases = useMemo(() => data ? [data.seed, ...data.held_out, data.control] : [], [data]);

  return <>
    <section className="hero tool-contract-hero">
      <div>
        <div className="experiment-badge"><FlaskConical size={15} /> {c.badge}</div>
        <h1>{c.title}</h1>
        <p>{c.subtitle}</p>
        <small className="experiment-boundary">{c.boundary}</small>
      </div>
    </section>

    {!data && !error && <section className="card tool-contract-loading">{c.loading}</section>}
    {error && <section className="card failure-card"><div className="error-box"><CircleAlert size={20} /><div><b>{c.error}</b><span>{error}</span></div></div></section>}

    {data && <>
      <section className="tool-contract-flow">
        <FlowCard n="1" title={c.seed} body={c.seedBody} icon={<CircleAlert size={18} />} />
        <ArrowRight className="flow-arrow" size={22} />
        <FlowCard n="2" title={c.diagnose} body={c.diagnoseBody} icon={<ShieldCheck size={18} />} />
        <ArrowRight className="flow-arrow" size={22} />
        <FlowCard n="3" title={c.patch} body={c.patchBody} icon={<Wrench size={18} />} />
        <ArrowRight className="flow-arrow" size={22} />
        <FlowCard n="4" title={c.validate} body={c.validateBody} icon={<Check size={18} />} />
      </section>

      <section className="card">
        <div className="card-heading"><div className="heading-title"><div className="number">1</div><h2>TD1 · {c.seed}</h2></div><span className="status-pill red">FAIL</span></div>
        <p className="tool-contract-request">{data.seed.test_case.input}</p>
        <div className="contract-comparison">
          <div><small>{c.actualArg}</small><code>product_name</code></div>
          <ArrowRight size={20} />
          <div><small>{c.requiredArg}</small><code>query</code></div>
        </div>
        <div className="cause-grid">
          <Metric label={c.failurePattern} value={data.failure_pattern.category} />
          <Metric label={c.targetSurface} value={data.root_cause.target_component} />
          <Metric label={c.rootCause} value={data.root_cause.root_cause} wide />
        </div>
      </section>

      <section className="card">
        <div className="card-heading"><div className="heading-title"><div className="number">2</div><h2>{c.patchDiff}</h2></div><span className="status-pill muted">tool_description</span></div>
        <div className="diff">
          <div><label>{c.before}<small>search_products</small></label><pre>{descriptionOf(data.patch.old_value)}</pre></div>
          <ArrowRight size={24} />
          <div><label>{c.after}<small>search_products</small></label><pre className="after-code">{descriptionOf(data.patch.proposed_value)}</pre></div>
        </div>
        <div className="frozen-banner">
          argument_schema · business logic · evaluator · ground truth · workflow_config
        </div>
      </section>

      <section className="card regression-table-card">
        <div className="card-heading"><div className="heading-title"><div className="number">3</div><h2>{c.matrix}</h2></div><span className="status-pill green">{c.noRegression}</span></div>
        <table>
          <thead><tr><th>Case</th><th>{c.role}</th><th>{c.request}</th><th>{c.baseline}</th><th>{c.candidate}</th><th>{c.result}</th></tr></thead>
          <tbody>{cases.map((item) => <CaseRow key={item.test_case.id} item={item} language={language} />)}</tbody>
        </table>
        <div className="frozen-regression-note"><b>{c.fixed}</b><span>{c.fixedBody}</span></div>
      </section>

      <section className="card regression-summary">
        <div className="card-heading"><div className="heading-title"><div className="number">4</div><h2>{c.decision}</h2></div></div>
        <div className="reg-metrics">
          <Metric label={c.baseline} value={`${data.regression_decision.baseline_pass_count}/${data.regression_decision.baseline_total}`} />
          <Metric label={c.candidate} value={`${data.regression_decision.candidate_pass_count}/${data.regression_decision.candidate_total}`} />
          <Metric label={c.improved} value={String(data.regression_decision.improved_test_ids.length)} />
          <Metric label={c.regressed} value={String(data.regression_decision.regressed_test_ids.length)} />
          <Metric label={c.decision} value={data.regression_decision.decision === "accept" ? c.accept : data.regression_decision.decision.toUpperCase()} />
        </div>
        <div className="decision-banner"><Check size={22} /><div><b>{data.regression_decision.decision === "accept" ? c.accept : data.regression_decision.decision.toUpperCase()}</b><span>{data.regression_decision.explanation}</span></div></div>
      </section>
    </>}
  </>;
}

function FlowCard({ n, title, body, icon }: { n: string; title: string; body: string; icon: React.ReactNode }) {
  return <div className="flow-card"><div className="flow-card-top"><span>{n}</span>{icon}</div><b>{title}</b><p>{body}</p></div>;
}

function Metric({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  return <div className={`metric ${wide ? "metric-wide" : ""}`}><small>{label}</small><b>{value}</b></div>;
}

function CaseRow({ item, language }: { item: ToolContractCaseResult; language: Language }) {
  const c = COPY[language];
  const role = item.role === "patch_derivation" ? c.seedRole : item.role === "held_out_validation" ? c.heldoutRole : c.controlRole;
  const changed = !item.baseline.passed && item.candidate.passed;
  const preserved = item.baseline.passed && item.candidate.passed;
  return <tr>
    <td><b>{item.test_case.id}</b></td>
    <td>{role}</td>
    <td>{item.test_case.input}</td>
    <td><span className={`table-status ${item.baseline.passed ? "green-status" : "red-status"}`}>{item.baseline.passed ? "PASS" : "FAIL"}</span><code className="argument-key">{argumentKey(item.baseline.tool_call_arguments)}</code></td>
    <td><span className={`table-status ${item.candidate.passed ? "green-status" : "red-status"}`}>{item.candidate.passed ? "PASS" : "FAIL"}</span><code className="argument-key">{argumentKey(item.candidate.tool_call_arguments)}</code></td>
    <td>{changed ? c.improved : preserved ? c.preserved : "—"}</td>
  </tr>;
}

function argumentKey(items: Array<Record<string, unknown>>): string {
  const first = items[0];
  if (!first) return "—";
  return Object.keys(first).join(", ") || "—";
}

function descriptionOf(value: Record<string, unknown>): string {
  return typeof value.description === "string" ? value.description : JSON.stringify(value, null, 2);
}
