"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, ChevronDown, CircleAlert, CirclePlay, Database, FileCode2, FlaskConical, Globe2, ListChecks, LockKeyhole, Play, RotateCcw, Settings2, ShieldCheck, Sparkles, Wrench, X } from "lucide-react";
import { mockAgentLab, parseRequest } from "../lib/mock-agentlab";
import { diagnoseRun, generatePatch, runCommerceRequest, runRegression, type DiagnosisResponse, type PatchResponse, type RegressionResponse } from "../lib/api";
import { t, type TranslationKey } from "../i18n";
import type { Language, RequestAnalysis, WorkflowState } from "../types/contracts";
import { PRODUCT_EXPERIMENTS, requestForProductExperiment, requestForTemplate, SCENARIO_TEMPLATES, type ProductExperimentMode, type ScenarioTemplateId } from "../lib/templates";
import { workflowStage } from "../lib/workflow";

const iconFor = (name: string) => name === "search_policy" ? <FileCode2 size={18} /> : name === "check_eligibility" ? <ShieldCheck size={18} /> : <Wrench size={18} />;

export default function Home() {
  const [language, setLanguage] = useState<Language>("zh");
  const [request, setRequest] = useState(() => requestForTemplate("promo", "zh"));
  const [activeTemplate, setActiveTemplate] = useState<ScenarioTemplateId | null>("promo");
  const [productExperimentMode, setProductExperimentMode] = useState<ProductExperimentMode>("normal");
  const [state, setState] = useState<WorkflowState>("ready");
  const [trace, setTrace] = useState<import("../types/contracts").ExecutionTrace | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [scenarioId, setScenarioId] = useState<string | null>("CS6");
  const [editedRegisteredRequest, setEditedRegisteredRequest] = useState(false);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResponse | null>(null);
  const [diagnosisLoading, setDiagnosisLoading] = useState(false);
  const [patchLoading, setPatchLoading] = useState(false);
  const [patchResult, setPatchResult] = useState<PatchResponse | null>(null);
  const [regressionResult, setRegressionResult] = useState<RegressionResponse | null>(null);
  const [regressionLoading, setRegressionLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runErrorTitle, setRunErrorTitle] = useState<TranslationKey>("taskIncomplete");
  const [snapshot] = useState(mockAgentLab);
  const parsed = useMemo(() => parseRequest(request, language), [request, language]);
  const isReady = state === "ready";
  const isFailure = state === "execution" || state === "execution_failed";
  const isDiagnosis = state === "diagnosed";
  const isPatch = state === "patch_ready";
  const isValidated = state === "validated";
  const stage = workflowStage(state);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const template = params.get("template") as ScenarioTemplateId | null;
    if (!template || !SCENARIO_TEMPLATES[template]) return;
    const selected = SCENARIO_TEMPLATES[template];
    const requestedExperiment = params.get("experiment");
    const productMode: ProductExperimentMode =
      template === "product" && requestedExperiment === "tool-contract"
        ? "tool_contract"
        : "normal";
    setProductExperimentMode(productMode);
    setRequest(
      template === "product"
        ? requestForProductExperiment(productMode, "zh")
        : selected.requests.zh,
    );
    setScenarioId(
      template === "product"
        ? PRODUCT_EXPERIMENTS[productMode].scenarioId
        : selected.scenarioId,
    );
    setActiveTemplate(template);
    setEditedRegisteredRequest(false);
    if (template === "custom") window.setTimeout(() => document.querySelector<HTMLTextAreaElement>("textarea")?.focus(), 0);
  }, []);

  const changeLanguage = (next: Language) => {
    if (activeTemplate === "product") {
      setRequest(requestForProductExperiment(productExperimentMode, next));
    } else if (activeTemplate) {
      setRequest(requestForTemplate(activeTemplate, next));
    }
    setLanguage(next);
  };

  const resetToTemplate = (templateId: ScenarioTemplateId | null = activeTemplate) => {
    const resolved = templateId && SCENARIO_TEMPLATES[templateId] ? templateId : "promo";
    const selected = SCENARIO_TEMPLATES[resolved];
    setState("ready");
    setTrace(null);
    setRunId(null);
    setDiagnosis(null);
    setPatchResult(null);
    setRegressionResult(null);
    setRunError(null);
    setRunErrorTitle("taskIncomplete");
    setScenarioId(
      resolved === "product"
        ? PRODUCT_EXPERIMENTS[productExperimentMode].scenarioId
        : selected.scenarioId,
    );
    setActiveTemplate(resolved);
    setEditedRegisteredRequest(false);
    setRequest(
      resolved === "product"
        ? requestForProductExperiment(productExperimentMode, language)
        : requestForTemplate(resolved, language),
    );
  };

  const selectProductExperiment = (mode: ProductExperimentMode) => {
    setProductExperimentMode(mode);
    setState("ready");
    setTrace(null);
    setRunId(null);
    setDiagnosis(null);
    setPatchResult(null);
    setRegressionResult(null);
    setRunError(null);
    setRunErrorTitle("taskIncomplete");
    setActiveTemplate("product");
    setEditedRegisteredRequest(false);
    setScenarioId(PRODUCT_EXPERIMENTS[mode].scenarioId);
    setRequest(requestForProductExperiment(mode, language));
  };

  return <div className="app-shell">
    <header className="topbar"><Link className="brand" href="/"><div className="brand-mark">A</div><div><strong>AgentLab</strong><small>{t(language, "brandTagline")}</small></div></Link><nav className="topnav"><Link className="active" href="/">{t(language, "home")}</Link><Link href="/runs">{t(language, "runs")}</Link><Link href="/failures">{t(language, "failures")}</Link><Link href="/patches">{t(language, "patches")}</Link><Link className={isValidated ? "active" : ""} href="/regression">{t(language, "regression")}</Link></nav><div className="top-actions"><span className="select-pill">◉　{t(language, "target")}: <b>Commerce Agent</b>⌄</span><span className="select-pill">⚙　{t(language, "environment")}: <b>Demo</b>⌄</span><Globe2 size={21} color="#172554" /><div className="language"><button className={language === "zh" ? "selected" : ""} onClick={() => changeLanguage("zh")}>中文</button><button className={language === "en" ? "selected" : ""} onClick={() => changeLanguage("en")}>EN</button></div><div className="avatar">Y</div></div></header>
    <aside className="sidebar"><div className="side-main"><SideItem href="/" active icon="⌂" label={t(language, "home")} /><SideItem href="/" icon="✦" label={t(language, "quickStart")} /></div><SideSection title={t(language, "templates")}><SideItem reloadDocument href="/?template=promo" icon="◈" label={t(language, "promo")} /><SideItem reloadDocument href="/?template=product" icon="▣" label={t(language, "product")} /><SideItem reloadDocument href="/?template=tool-contract" icon="⌘" label={t(language, "toolContractRepair")} /><SideItem reloadDocument href="/?template=order" icon="▤" label={t(language, "order")} /><SideItem reloadDocument href="/?template=returns" icon="▱" label={t(language, "returns")} /><SideItem reloadDocument href="/?template=custom" icon="□" label={t(language, "custom")} /></SideSection><SideSection title={t(language, "settings")}><SideItem href="/settings/agent" icon="✣" label={t(language, "config")} /><SideItem href="/settings/benchmarks" icon="▦" label={t(language, "tests")} /><SideItem href="/settings/evaluator" icon="✓" label={t(language, "evaluator")} /><SideItem href="/settings/data" icon="▤" label={t(language, "data")} /></SideSection><div className="sidebar-note"><b>AgentLab</b><span>{t(language, "sidebarNote")}</span></div></aside>
    <main className="main"><Hero stage={stage} language={language} state={state} />
      <div className="columns"><div className="content">
        {isReady && <ReadyCard language={language} request={request} activeTemplate={activeTemplate} editedRegisteredRequest={editedRegisteredRequest} setRequest={(value) => { if (activeTemplate && scenarioId) setEditedRegisteredRequest(true); setRequest(value); setScenarioId(null); setActiveTemplate(null); }} parsed={parsed} onRun={async () => { setRunError(null); setRunErrorTitle("taskIncomplete"); try { const result = await runCommerceRequest(request, scenarioId); setTrace(result); setRunId(result.run_id); setState(result.error ? "execution_failed" : "execution"); } catch (error) { setRunError(error instanceof Error ? error.message : String(error)); } }} onReset={() => resetToTemplate()} />}
        {!isReady && <RequestSummary language={language} request={request} parsed={parsed} />}
        {isReady && <ExecutionWaiting language={language} />}
        {isFailure && trace && <ExecutionFailure language={language} trace={trace} evaluation={trace.evaluation ?? null} evaluationAvailable={trace.evaluation_available} onDiagnose={async () => { if (!runId) return; setDiagnosisLoading(true); setRunError(null); try { const result = await diagnoseRun(runId); if (result.status === "evaluation_unavailable") { setRunErrorTitle("evaluationUnavailable"); setRunError(t(language, "evaluationUnavailable")); } else if (result.status === "no_failure") { setRunErrorTitle("noFailureDetected"); setRunError(t(language, "noFailureDetected")); } else { setDiagnosis(result); setState("diagnosed"); } } catch (error) { setRunErrorTitle("taskIncomplete"); setRunError(error instanceof Error ? error.message : String(error)); } finally { setDiagnosisLoading(false); } }} onReset={() => resetToTemplate()} diagnosisLoading={diagnosisLoading} />}
        {isReady && runError && <section className="card failure-card"><div className="error-box"><CircleAlert size={20} /><div><b>{t(language, "taskIncomplete")}</b><span>{runError}</span></div></div></section>}
        {isFailure && runError && <section className="card failure-card"><div className="error-box"><CircleAlert size={20} /><div><b>{t(language, runErrorTitle)}</b><span>{runError}</span></div></div></section>}
        {isDiagnosis && diagnosis && trace && <Diagnosis language={language} diagnosis={diagnosis} trace={trace} patchLoading={patchLoading} onPatch={async () => { if (!runId) return; setPatchLoading(true); setRunError(null); try { const result = await generatePatch(runId); setPatchResult(result); if (result.status === "patch_ready" && result.patch) setState("patch_ready"); else setRunError(result.message ?? t(language, "patchUnavailable")); } catch (error) { setRunError(error instanceof Error ? error.message : String(error)); } finally { setPatchLoading(false); } }} />}
        {isDiagnosis && runError && <section className="card failure-card"><div className="error-box"><CircleAlert size={20} /><div><b>{t(language, "patchUnavailable")}</b><span>{runError}</span></div></div><div className="card-actions"><button className="secondary" onClick={() => setRunError(null)}>{t(language, "returnDiagnosis")}</button></div></section>}
        {isPatch && patchResult?.patch && <PatchReady language={language} patch={patchResult.patch} failurePattern={patchResult.failure_pattern} rootCause={patchResult.root_cause} regressionLoading={regressionLoading} onApply={async () => { if (!runId) return; setRegressionLoading(true); setRunError(null); try { const result = await runRegression(runId); setRegressionResult(result); setState("validated"); } catch (error) { setRunError(error instanceof Error ? error.message : String(error)); } finally { setRegressionLoading(false); } }} onBack={() => setState("diagnosed")} />}
        {isPatch && runError && <section className="card failure-card"><div className="error-box"><CircleAlert size={20} /><div><b>{t(language, "regressionFailed")}</b><span>{runError}</span></div></div></section>}
        {isValidated && regressionResult && <Regression language={language} result={regressionResult} onReset={() => resetToTemplate()} />}
      </div><RightRail language={language} state={state} trace={trace} patch={patchResult?.patch ?? null} regression={regressionResult} /></div>
    </main>
  </div>;
}

function SideItem({ icon, label, href, active = false, disabled = false }: { icon: string; label: string; href: string; active?: boolean; reloadDocument?: boolean; disabled?: boolean }) { const unsupported = href.includes("template=order") || href.includes("template=returns"); return disabled || unsupported ? <span className="side-item disabled" style={{ cursor: "not-allowed", opacity: 0.58 }}><span>{icon}</span>{label}<small style={{ marginLeft: "auto", whiteSpace: "nowrap", fontSize: 10 }}>{t("zh", "unsupportedStatus")}</small></span> : <a className={`side-item ${active ? "selected" : ""}`} href={href}><span>{icon}</span>{label}</a>; }
function SideSection({ title, children }: { title: string; children: React.ReactNode }) { return <section className="side-section"><h4>{title}</h4>{children}</section>; }

function Hero({ language, state }: { stage: number; language: Language; state: WorkflowState }) {
  const activeStage = state === "ready" ? 1 : state === "execution" ? 2 : state === "execution_failed" ? 3 : state === "diagnosed" ? 4 : state === "patch_ready" ? 5 : 6;
  const steps = language === "zh"
    ? [["Scenario", "场景"], ["Agent Execution", "执行"], ["Evaluation", "评估"], ["Failure / Root Cause", "失败定位"], ["Patch", "补丁"], ["Regression", "回归"], ["Coverage", "覆盖"]]
    : [["Scenario", "Input"], ["Agent Execution", "Trace"], ["Evaluation", "Verdict"], ["Failure / Root Cause", "Diagnosis"], ["Patch", "Bounded fix"], ["Regression", "Validation"], ["Coverage", "Remaining gaps"]];
  const title = language === "zh"
    ? state === "ready" ? "Agent 实验工作台" : state === "execution" || state === "execution_failed" ? "Agent Execution · 运行证据" : state === "diagnosed" ? "Failure → Root Cause" : state === "patch_ready" ? "Patch Diff · 受约束修复" : "Regression · 接受决策"
    : state === "ready" ? "Agent Experiment Workbench" : state === "execution" || state === "execution_failed" ? "Agent Execution · Evidence" : state === "diagnosed" ? "Failure → Root Cause" : state === "patch_ready" ? "Patch Diff · Bounded Repair" : "Regression · Acceptance Decision";
  const subtitle = language === "zh" ? "从 Scenario 到 Coverage：运行、评估、诊断并验证每一次 Harness 修改。" : "From Scenario to Coverage: run, evaluate, diagnose, and validate every Harness change.";
  return <section className="hero"><div><h1>{title}</h1><p>{subtitle}</p></div><div className="progress experiment-pipeline">{steps.map(([label, detail], index) => <div className={`progress-step ${index + 1 < activeStage ? "done" : index + 1 === activeStage ? "current" : ""}`} key={label}><div className="step-circle">{index + 1 < activeStage ? <Check size={15} /> : index + 1}</div><div><b>{label}</b><small>{detail}</small></div>{index < steps.length - 1 && <ArrowRight size={17} className="progress-arrow" />}</div>)}</div></section>;
}

function ReadyCard({ language, request, activeTemplate, editedRegisteredRequest, setRequest, parsed, onRun, onReset }: { language: Language; request: string; activeTemplate: ScenarioTemplateId | null; editedRegisteredRequest: boolean; setRequest: (value: string) => void; parsed: RequestAnalysis; onRun: () => void; onReset: () => void }) { const template = activeTemplate ? SCENARIO_TEMPLATES[activeTemplate] : null; const registeredCase = template?.scenarioId && template.testCaseId ? template.testCaseId : null; return <><section className="card request-card"><CardHeading number="1" title={t(language, "request")}><div className="heading-actions"><button className="ghost">✧　{t(language, "sample")} <ChevronDown size={14} aria-hidden="true" /></button><button className="ghost" onClick={onReset}>{t(language, "clear")}</button></div></CardHeading>{registeredCase && <div className="request-context-status">{t(language, "registeredScenario")} · {registeredCase}</div>}{editedRegisteredRequest && <div className="request-context-notice">{t(language, "customRequestNotice")}</div>}{!registeredCase && !editedRegisteredRequest && activeTemplate === "custom" && <div className="request-context-status">{t(language, "customScenario")}</div>}<textarea value={request} onChange={(event) => setRequest(event.target.value)} maxLength={1000} /><div className="request-footer"><span>{request.length}/1000</span><button className="primary" onClick={onRun}><Play size={16} fill="currentColor" /> {t(language, "run")}</button><button className="secondary" onClick={onReset}><RotateCcw size={16} /> {t(language, "reset")}</button></div></section><ParsedCard language={language} parsed={parsed} request={request} /></>; }
function RequestSummary({ language, request, parsed }: { language: Language; request: string; parsed: RequestAnalysis }) { return <><section className="card request-summary"><CardHeading number="1" title={t(language, "request")}><span className="status-pill muted">✓ {t(language, "executed")}</span></CardHeading><p>{request}</p></section><ParsedCard language={language} parsed={parsed} request={request} /></>; }
function ParsedCard({ language, parsed, request }: { language: Language; parsed: RequestAnalysis; request: string }) { const productRequest = /跑鞋|running shoes/i.test(request); const items = productRequest ? [{ icon: "◉", label: t(language, "intent"), value: parsed.intent ?? "—" }, { icon: "◎", label: language === "zh" ? "标准化商品" : "Normalized product", value: language === "zh" ? "跑鞋" : "Running shoes" }, { icon: "◒", label: language === "zh" ? "可购买性" : "Availability", value: language === "zh" ? "仅展示有库存商品" : "In-stock products only" }, { icon: "▣", label: language === "zh" ? "输出形式" : "Output", value: language === "zh" ? "可购买商品列表" : "Purchasable product list" }] : [{ icon: "◉", label: t(language, "intent"), value: parsed.intent ?? "—" }, { icon: "◌", label: t(language, "amount"), value: parsed.amount ?? t(language, "notDetected") }, { icon: "□", label: t(language, "date"), value: parsed.paymentDate ?? t(language, "notDetected") }, { icon: "▣", label: t(language, "orderType"), value: parsed.orderType ?? t(language, "notDetected") }]; return <section className="card parsed-card"><CardHeading number="2" title={t(language, "parsed")}><button className="ghost">⟳　{t(language, "reparse")}</button></CardHeading><p className="muted-text">{t(language, "parsedDescription")}</p><div className="parsed-grid">{items.map(item => <div className="parsed-item" key={item.label}><span className="item-icon">{item.icon}</span><div><small>{item.label}</small><b>{item.value}</b></div></div>)}</div><div className="details"><ChevronDown size={16} /> {t(language, "details")}</div></section>; }
function ExecutionWaiting({ language }: { language: Language }) { return <section className="card execution-wait"><CardHeading number="3" title={t(language, "execution")}><span className="ghost">◷　{t(language, "waiting")}</span></CardHeading><div className="empty-execution"><div className="empty-icon">⌁</div><div><b>{t(language, "waitingTitle")}</b><p>{t(language, "waitingBody")}</p></div><ArrowRight size={28} /></div></section>; }
function ExecutionFailure({ language, trace, evaluation, evaluationAvailable, onDiagnose, onReset, diagnosisLoading }: { language: Language; trace: import("../types/contracts").ExecutionTrace; evaluation: import("../types/contracts").EvaluationResult | null; evaluationAvailable: boolean | undefined; onDiagnose: () => void; onReset: () => void; diagnosisLoading: boolean }) {
  const events = trace.tool_events ?? [];
  const nextTool = trace.error?.match(/for ([a-z_]+)/i)?.[1] ?? null;
  const limit = trace.error?.match(/workflow\.max_steps=?\s*(\d+)/i)?.[1] ?? null;
  const taskPassed = evaluationAvailable === true && evaluation?.passed === true;
  const taskFailed = evaluationAvailable === true && evaluation?.passed === false;
  const statusLabel = trace.error ? t(language, "executionFailed") : taskPassed ? t(language, "taskPassed") : taskFailed ? t(language, "taskFailed") : t(language, "executionCompleted");
  const statusClass = trace.error || taskFailed ? "red" : taskPassed ? "green" : "muted";
  return <section className="card failure-card"><CardHeading number="3" title={t(language, "agentExecution")}><span className={`status-pill ${statusClass}`}>● {statusLabel}</span></CardHeading>
    <div className="timeline">{trace.tool_calls.map((tool, index) => { const event = events[index]; return <TimelineRow key={`${tool}-${index}`} n={String(index + 1)} tool={tool} label={tool === "search_policy" ? t(language, "findPolicy") : tool === "check_eligibility" ? t(language, "checkGift") : tool} status={event?.error ? t(language, "executionFailed") : t(language, "toolCompleted")} argumentsText={trace.tool_call_arguments?.[index] ? formatArguments(trace.tool_call_arguments[index]) : "—"} result={event?.error ?? (event?.result !== undefined ? formatResult(event.result, language) : t(language, "notRecorded"))} ok={!event?.error} />; })}{nextTool && !trace.tool_calls.includes(nextTool) && <TimelineRow n={String(trace.tool_calls.length + 1)} tool={nextTool} label={nextTool === "check_eligibility" ? t(language, "checkGift") : nextTool} status={t(language, "stepNotReached")} argumentsText="—" result={t(language, "notReached")} />}</div>
    {trace.error && <div className="error-box"><CircleAlert size={20} /><div><b>{t(language, "executionFailed")}</b><span>{limit ? `${t(language, "executionIncomplete")} ${t(language, "executionLimit")}: workflow.max_steps = ${limit}` : trace.error}</span>{nextTool && !trace.tool_calls.includes(nextTool) && <small>{t(language, "nextRequired")}: {nextTool}</small>}</div><strong>{t(language, "fail")}</strong></div>}
    {!trace.error && <div id="task-evaluation" className={`evaluation-box ${taskFailed ? "evaluation-failed" : ""}`}><div><b>{t(language, "taskEvaluation")}</b><span>{evaluationAvailable ? (evaluation?.explanation ?? statusLabel) : t(language, "unregisteredEvaluationBody")}</span></div><strong>{evaluationAvailable ? (taskPassed ? t(language, "pass") : t(language, "fail")) : t(language, "unregisteredEvaluation")}</strong></div>}
    <details className="details"><summary><ChevronDown size={16} /> {t(language, "technicalTrace")} ({t(language, "executionTrace")})</summary><TraceEvidence language={language} trace={trace} /></details>
    <div className="failure-actions">{(trace.error || taskFailed) && <button className="primary" disabled={diagnosisLoading} onClick={onDiagnose}>{diagnosisLoading ? t(language, "diagnosisLoading") : t(language, "diagnoseFailure")} <ArrowRight size={16} /></button>}{taskPassed && <button className="primary" onClick={() => document.getElementById("task-evaluation")?.scrollIntoView({ behavior: "smooth" })}>{t(language, "viewEvaluation")} <ArrowRight size={16} /></button>}{!trace.error && !taskFailed && !taskPassed && <button className="primary" onClick={onReset}>{t(language, "editRequest")} <ArrowRight size={16} /></button>}{!trace.error && !taskFailed && <button className="secondary" onClick={onReset}>{t(language, "runAnotherRequest")}</button>}</div>
  </section>;
}
function TimelineRow({ n, tool, label, status, argumentsText, result, ok = false }: { n: string; tool: string; label: string; status: string; argumentsText: string; result: string; ok?: boolean }) { return <div className="timeline-row"><div className={`timeline-dot ${ok ? "ok" : "pending"}`}>{ok ? <Check size={14} /> : n}</div><div className="tool-label"><b>{tool}</b><small>{label}</small><small>{argumentsText}</small></div><span className={`tool-result ${ok ? "success" : "pending-text"}`}>{status}</span><span className={`tool-result ${ok ? "success" : "pending-text"}`}>{result}</span></div>; }
function formatArguments(value: Record<string, unknown>): string { return Object.entries(value).map(([key, item]) => `${key} = ${String(item)}`).join(", "); }
function formatResult(value: unknown, language?: Language): string { if (Array.isArray(value) && value.length === 0) return language ? t(language, "noMatch") : "[]"; if (Array.isArray(value) && value[0] && typeof value[0] === "object" && "id" in value[0] && String((value[0] as { id?: unknown }).id).startsWith("POLICY_")) { const policy = value[0] as { id: string; starts_at?: string; ends_at?: string; min_amount?: number; gift?: string }; return language === "zh" ? `已找到适用政策：${policy.id}（${policy.starts_at ?? ""} 至 ${policy.ends_at ?? ""}，最低消费 ${policy.min_amount ?? "—"} 元，赠品 ${policy.gift ?? "—"}）` : `Applicable policy found: ${policy.id} (${policy.starts_at ?? ""} to ${policy.ends_at ?? ""}, minimum ${policy.min_amount ?? "—"}, gift ${policy.gift ?? "—"})`; } if (Array.isArray(value) && value[0] && typeof value[0] === "object" && "name" in value[0]) { const product = value[0] as { name?: string; price?: number; stock?: number }; const name = language === "zh" && product.name === "Running Shoes" ? "跑鞋（Running Shoes）" : product.name ?? "—"; return language === "zh" ? `商品：${name} · 价格 ${product.price ?? "—"} 元 · 库存 ${product.stock ?? "—"}` : `Product: ${name} · Price ${product.price ?? "—"} · Stock ${product.stock ?? "—"}`; } return typeof value === "string" ? value : JSON.stringify(value); }
function humanRoot(language: Language, value: string): string {
  if (language !== "zh") return value;
  const lower = value.toLowerCase();
  if (lower.includes("workflow step budget")) return "工作流最大执行步数不足，导致必要的下一步工具调用无法继续执行。";
  if (lower.includes("registered argument contract")) return "Agent 选择了正确工具，但实际参数不满足该工具已注册的参数契约。";
  return value;
}
function humanEvaluation(language: Language, value: string): string {
  if (language !== "zh") return value;
  const lower = value.toLowerCase();
  if (lower.includes("all deterministic commerce checks passed")) return "所有确定性 Commerce 检查均通过。";
  if (lower.includes("required eligibility decision")) return "任务未完成：尚未产生必要的赠品资格判断。";
  if (lower.includes("required tool") && lower.includes("was not called")) return "任务未完成：必要工具没有按预期执行。";
  if (lower.includes("candidate improved") && lower.includes("no correctness regressions")) return "候选版本修复了失败案例，且没有新增正确性回退。";
  if (lower.includes("expected execution success") && lower.includes("error")) return "执行失败：工具调用参数无法满足当前工具要求。";
  return value;
}
function humanFailureCategory(language: Language, value: string): string {
  if (language !== "zh") return value;
  if (value === "workflow_step_limit") return "工作流步数不足（workflow_step_limit）";
  if (value === "tool_argument_schema_failure") return "工具参数契约不匹配（tool_argument_schema_failure）";
  return value;
}
function humanPatchText(language: Language, value: string): string {
  if (language !== "zh") return value;
  const lower = value.toLowerCase();
  if (lower.includes("step-limit failure") || lower.includes("workflow step-limit failures")) return "Trace 证明失败由工作流步数上限触发。";
  if (lower.includes("allow the required workflow step")) return "允许执行被当前步数预算阻断的下一项必要工具调用。";
  if (lower.includes("additional workflow step may increase latency") || lower.includes("additional step may increase latency")) return "增加一个执行步骤可能带来少量延迟或成本，并可能允许非必要工具调用。";
  if (lower.includes("violating the registered contract")) return "Trace 证明 Agent 已选择正确工具，但提交的参数键违反了该工具的已注册参数契约。";
  if (lower.includes("make the registered argument contract explicit")) return "在现有工具说明中显式补充参数格式，让 Router 能按照已注册契约生成参数。";
  if (lower.includes("undocumented aliases")) return "更严格的参数说明可能降低对未文档化别名的兼容性，因此需要回归验证。";
  return value;
}
function patchValueSummary(value: Record<string, unknown>): string {
  if (typeof value.max_steps === "number") return `max_steps = ${value.max_steps}`;
  if (typeof value.name === "string" && typeof value.description === "string") return `${value.name} · tool description`;
  if (typeof value.system_prompt === "string") return "system_prompt";
  return Object.keys(value).join(", ") || "—";
}
function TraceEvidence({ language, trace }: { language: Language; trace: import("../types/contracts").ExecutionTrace }) { return <div className="trace-evidence"><div><b>{t(language, "runId")}</b><span>{trace.test_id}</span></div><div><b>{t(language, "agentVersionLabel")}</b><span>{trace.agent_version}</span></div><div><b>{t(language, "toolCalls")}</b><code>{JSON.stringify(trace.tool_events ?? [], null, 2)}</code></div><div><b>{t(language, "arguments")}</b><code>{JSON.stringify(trace.tool_call_arguments ?? [], null, 2)}</code></div><div><b>{t(language, "toolOutput")}</b><code>{trace.output || "—"}</code></div><div><b>{t(language, "latency")}</b><span>{trace.latency_seconds == null ? "—" : `${trace.latency_seconds.toFixed(6)}s`}</span></div><div><b>{t(language, "traceError")}</b><code>{trace.error ?? t(language, "noError")}</code></div></div>; }
function Diagnosis({ language, diagnosis, trace, onPatch, patchLoading }: { language: Language; diagnosis: DiagnosisResponse; trace: import("../types/contracts").ExecutionTrace; onPatch: () => void; patchLoading: boolean }) {
  const evaluation = diagnosis.evaluation;
  const pattern = diagnosis.failure_pattern;
  const root = diagnosis.root_cause;
  const nextTool = trace.error?.match(/for ([a-z_]+)/i)?.[1] ?? null;
  const isToolContractFailure = pattern?.category === "tool_argument_schema_failure";
  const lastEvent = (trace.tool_events ?? []).at(-1);
  const lastResult = lastEvent?.error ?? (lastEvent?.result !== undefined ? formatResult(lastEvent.result, language) : null);
  const failedRules = Object.entries(evaluation?.rule_scores ?? {}).filter(([, score]) => score < 1).map(([name, score]) => `${name}: ${score}`);
  const executionLines = [
    ...trace.tool_calls.map(tool => `${tool} ✓`),
    trace.tool_call_arguments?.length ? `${language === "zh" ? "实际参数" : "Observed arguments"}: ${formatArguments(trace.tool_call_arguments.at(-1) ?? {})}` : "",
    lastResult ? `${language === "zh" ? "结果" : "Result"}: ${lastResult}` : "",
    nextTool ? `${nextTool}: ${t(language, "stepNotReached")}` : "",
    trace.error ?? "",
  ].filter(Boolean);
  const evidenceLines = isToolContractFailure
    ? (root?.evidence ?? [])
    : [
        ...trace.tool_calls.map(tool => `✓ ${tool} ${t(language, "selectedCorrectly")}`),
        ...(lastResult ? [`→ ${lastResult}`] : []),
        ...(nextTool ? [`✓ ${nextTool} ${t(language, "wasNotExecuted")}`] : []),
        ...(trace.error ? [`→ ${trace.error}`] : []),
      ];

  return <section className="card diagnosis-card">
    <CardHeading number="3" title={t(language, "diagnosis")}><span className="status-pill red">{t(language, "failureTransition")}</span></CardHeading>
    <div className="chain">
      <ChainCard n="1" title="Execution Trace" lines={executionLines} />
      <ArrowRight className="chain-arrow" />
      <ChainCard n="2" title="Evaluation" lines={[evaluation?.passed ? t(language, "pass") : t(language, "taskIncompleteChain"), humanEvaluation(language, evaluation?.explanation ?? "—"), ...failedRules]} />
      <ArrowRight className="chain-arrow" />
      <ChainCard n="3" title="Failure Pattern" lines={[humanFailureCategory(language, pattern?.category ?? "—"), `${t(language, "affected")}: ${pattern?.affected_test_ids.join(", ") || "—"}`, `${language === "zh" ? "严重程度" : "Severity"}: ${language === "zh" && pattern?.severity === "medium" ? "中" : pattern?.severity ?? "—"}`]} />
      <ArrowRight className="chain-arrow" />
      <ChainCard n="4" title="Root Cause" lines={[humanRoot(language, root?.root_cause ?? "—"), `${t(language, "targetLabel")}${root?.target_component ?? "—"}`, `${t(language, "confidenceLabel")}${root?.confidence ?? "—"}`]} />
    </div>
    <div className="evidence-grid">
      <div className="evidence-box"><h3>⌁ {t(language, "evidence")}</h3><ul>{evidenceLines.map((line, index) => <li key={`${index}-${line}`}>{line}</li>)}</ul></div>
      <div className="impact-box"><h3>{t(language, "affectedScope")}</h3><div className="case-pills">{(pattern?.affected_test_ids ?? []).map(id => <span key={id} className="bad">× {id}</span>)}</div></div>
    </div>
    <div className="card-actions"><button className="secondary">▣ {t(language, "fullEvidence")}</button><button className="primary" disabled={patchLoading} onClick={onPatch}>{patchLoading ? t(language, "patchLoading") : t(language, "viewPatch")} <ArrowRight size={16} /></button></div>
  </section>;
}
function ChainCard({ n, title, lines }: { n: string; title: string; lines: string[] }) { return <div className="chain-card"><div className="chain-number">{n}</div><h4>{title}</h4>{lines.map(line => <p key={line}>{line}</p>)}</div>; }
function PatchReady({ language, patch, failurePattern, rootCause, regressionLoading, onApply, onBack }: { language: Language; patch: import("../types/contracts").HarnessPatch; failurePattern: import("../types/contracts").FailurePattern | null; rootCause: import("../types/contracts").RootCauseAnalysis | null; regressionLoading: boolean; onApply: () => void; onBack: () => void }) {
  return <><section className="card cause-summary"><CardHeading number="1" title={t(language, "cause")} /><div className="cause-grid"><Metric label="Failure Pattern" value={humanFailureCategory(language, failurePattern?.category ?? "—")} bad /><Metric label={t(language, "affected")} value={failurePattern?.affected_test_ids.join(", ") ?? "—"} /><Metric label={t(language, "targetComponent")} value={patch.target_component} blue /><Metric label={t(language, "patchability")} value={t(language, "yes")} good /></div></section><section className="card patch-card"><CardHeading number="2" title={t(language, "patchTitle")}><span className="status-pill green">✓ {t(language, "boundedChange")}</span></CardHeading><p className="muted-text">{humanPatchText(language, patch.reason)}</p><div className="diff"><div><label>− {t(language, "before")}</label><pre>{JSON.stringify(patch.old_value, null, 2)}</pre></div><ArrowRight size={31} /><div><label className="green-text">＋ {t(language, "after")}</label><pre className="after-code">{JSON.stringify(patch.proposed_value, null, 2)}</pre></div></div><div className="patch-fields"><p><b>{t(language, "supportingFailures")}:</b> {patch.supporting_failure_pattern_ids.join(", ")}</p><p><b>{t(language, "expectedEffect")}:</b> {humanPatchText(language, patch.expected_effect)}</p><p><b>{t(language, "regressionRisk")}:</b> {humanPatchText(language, patch.regression_risk)}</p><p><b>{t(language, "provenance")}:</b> {humanRoot(language, rootCause?.root_cause ?? "—")}</p></div><div className="card-actions"><button className="secondary" onClick={onBack}>‹ {t(language, "backDiagnosis")}</button><button className="primary" disabled={regressionLoading} onClick={onApply}><Play size={16} fill="currentColor" /> {regressionLoading ? t(language, "regressionLoading") : t(language, "applyNextStage")}</button></div></section></>;
}
function Metric({ label, value, bad = false, blue = false, good = false }: { label: string; value: string; bad?: boolean; blue?: boolean; good?: boolean }) { return <div className="metric"><small>{label}</small><b className={`${bad ? "red-text" : ""}${blue ? " blue-text" : ""}${good ? " green-text" : ""}`}>{value}</b></div>; }
function Regression({ language, result, onReset }: { language: Language; result: RegressionResponse; onReset: () => void }) {
  const decision = result.regression_decision;
  const candidateById = new Map(result.candidate_evaluations.map(item => [item.test_id, item]));
  return <><section className="card regression-summary"><CardHeading number="1" title={t(language,"regressionSummary")}><span className={`status-pill ${decision.decision === "accept" ? "green" : "red"}`}>{decision.decision.toUpperCase()}</span></CardHeading><div className="reg-metrics"><Metric label={t(language,"baseline")} value={`${decision.baseline_pass_count} / ${decision.baseline_total}`} /><Metric label={t(language,"candidate")} value={`${decision.candidate_pass_count} / ${decision.candidate_total}`} good={decision.candidate_pass_count >= decision.baseline_pass_count} /><Metric label={t(language,"improvedCases")} value={String(decision.improved_test_ids.length)} good={decision.improved_test_ids.length > 0} /><Metric label={t(language,"regressions")} value={String(decision.regressed_test_ids.length)} bad={decision.regressed_test_ids.length > 0} /><Metric label={t(language,"decision")} value={decision.decision.toUpperCase()} good={decision.decision === "accept"} /></div><p className="muted-text">{humanEvaluation(language, decision.explanation)}</p></section><section className="card regression-table-card"><CardHeading number="2" title={t(language,"frozenComparison")}><span className="muted-text">{decision.baseline_version} → {decision.candidate_version}</span></CardHeading><table><thead><tr><th>{t(language,"test")}</th><th>{t(language,"baseline")}</th><th>{t(language,"candidate")}</th><th>{t(language,"change")}</th><th>{t(language,"explanation")}</th></tr></thead><tbody>{result.baseline_evaluations.map(item => { const candidate = candidateById.get(item.test_id); const changed = !candidate ? "—" : item.passed === candidate.passed ? t(language,"unchanged") : candidate.passed ? t(language,"improved") : t(language,"regressions"); return <tr key={item.test_id}><td><b>{item.test_id}</b></td><td><span className={`table-status ${item.passed ? "green-status" : "red-status"}`}>{item.passed ? "PASS" : "FAIL"}</span></td><td><span className={`table-status ${candidate?.passed ? "green-status" : "red-status"}`}>{candidate?.passed ? "PASS" : "FAIL"}</span></td><td className={changed === t(language,"improved") ? "green-text" : ""}>{changed}</td><td>{humanEvaluation(language, candidate?.explanation ?? "—")}</td></tr>; })}</tbody></table><div className="rate-banner">▥ {t(language,"passRate")} <b>{decision.baseline_pass_count} / {decision.baseline_total} → {decision.candidate_pass_count} / {decision.candidate_total}</b> · {t(language,"improved")} <b>{decision.improved_test_ids.length}</b> · {t(language,"regressions")} <b>{decision.regressed_test_ids.length}</b></div><div className="decision-banner"><Check size={22}/><div><b>{decision.decision.toUpperCase()}</b><span>{humanEvaluation(language, decision.explanation)}</span></div></div><div className="card-actions"><button className="secondary" onClick={onReset}>‹ {t(language,"finishRepair")}</button><button className="primary">▣ {t(language,"fullEvidence")}</button></div></section></>;
}
function CardHeading({ number, title, children }: { number: string; title: string; children?: React.ReactNode }) { return <div className="card-heading"><div className="heading-title"><span className="number">{number}</span><h2>{title}</h2></div>{children}</div>; }
function RightRail({ language, state, trace, patch, regression }: { language: Language; state: WorkflowState; trace: import("../types/contracts").ExecutionTrace | null; patch: import("../types/contracts").HarnessPatch | null; regression: RegressionResponse | null }) {
  const baselineVersion = trace?.agent_version ?? "commerce-v1";
  const candidateVersion = regression?.regression_decision.candidate_version ?? (patch?.target_component === "tool_description" ? "commerce-v3-tool-description" : "commerce-v2");
  const maxSteps = trace?.error?.match(/workflow\.max_steps=?\s*(\d+)/i)?.[1] ?? (baselineVersion === "commerce-v2" ? "3" : "2");
  const surfaces = ["system_prompt", "tool_description", "context", "workflow_config"];
  const frozen = ["scenario", "ground truth", "evaluator", "benchmark", "model/router"];
  const currentStage = workflowStage(state);
  const changedSurface = patch?.target_component ?? null;
  return <aside className="right-rail">
    <section className="card rail-card harness-summary">
      <h3><Settings2 size={18}/> {state === "ready" ? t(language, "currentAgent") : t(language, "runOverview")}<span className="status-pill muted">{state === "validated" ? t(language, "decisionAccept") : t(language, "agentVersion")}</span></h3>
      <div className="harness-section"><b>{t(language, "target")}</b><div className="harness-value"><span>{t(language, "targetAgentLabel")}</span><strong>Commerce Agent</strong></div><div className="harness-value"><span>{t(language, "agentVersion")}</span><strong>{state === "validated" ? `${baselineVersion} → ${candidateVersion}` : baselineVersion}</strong></div></div>
      <div className="harness-section"><b>{t(language, "baseConfig")}</b>
        {patch && (state === "patch_ready" || state === "validated")
          ? <><div className="harness-compare"><span>{t(language, "baseline")}<strong>{baselineVersion}<br/>{patchValueSummary(patch.old_value)}</strong></span><b>→</b><span>{t(language, "candidate")}<strong>{candidateVersion}<br/>{patchValueSummary(patch.proposed_value)}</strong></span></div><div className="harness-value"><span>{t(language, "changedField")}</span><strong>{changedSurface}</strong></div></>
          : <div className="harness-value"><span>workflow_config</span><strong>max_steps = {maxSteps}</strong></div>}
      </div>
      <div className="harness-section"><b>{t(language, "editable")}</b><div className="surface-chips">{surfaces.map(surface => <span key={surface}>{surface}</span>)}</div></div>
      <div className="harness-section"><b>{t(language, "frozen")}</b><div className="surface-chips frozen-chips">{frozen.map(item => <span key={item}>{item}</span>)}</div></div>
      <Link className="config-link" href="/settings/agent">{t(language, "viewFullConfig")} <ArrowRight size={14}/></Link>
    </section>
    <section className="card rail-card"><h3><Wrench size={18}/> {t(language,"availableTools")}</h3>{["search_products","search_policy","check_eligibility"].map(name=><div className="tool-card" key={name}>{iconFor(name)}<div><b>{name}</b><small>{name==="search_products"?t(language,"searchProductsDesc"):name==="search_policy"?t(language,"searchPolicyDesc"):t(language,"checkEligibilityDesc")}</small></div></div>)}</section>
    <section className="card rail-card next-card"><h3><ListChecks size={18}/> {t(language,"next")}</h3>{["run","evaluate","diagnose","repair","validate"].map((key,i)=><div key={key} className={`next-row ${i+1===currentStage?"current":i+1<currentStage?"done":""}`}><span>{i+1}</span>{t(language,key as "run"|"evaluate"|"diagnose"|"repair"|"validate")}</div>)}</section>
  </aside>;
}

