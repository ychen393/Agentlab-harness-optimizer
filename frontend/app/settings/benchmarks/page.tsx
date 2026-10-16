"use client";

import { useEffect, useState } from "react";
import { RouteShell } from "../../../components/route-shell";
import { fetchBenchmarks, type BenchmarkCase, type BenchmarkResponse } from "../../../lib/api";
import { t } from "../../../i18n";
import type { Language } from "../../../types/contracts";

const groups = [
  ["fixed_regression", "fixedRegression", "fixedRegressionBody"],
  ["adaptive_challenges", "adaptiveChallenges", "adaptiveChallengesBody"],
  ["coverage_exploration", "coverageExploration", "coverageExplorationBody"],
] as const;

function groundTruthSummary(item: BenchmarkCase, language: Language): string[] {
  const truth = item.ground_truth;
  const lines = [`${t(language, "expectedPathLabel")}: ${truth.expected_tool_calls?.join(" → ") ?? truth.expected_tool}`];
  if (truth.expected_policy_id) lines.push(`${language === "zh" ? "政策" : "Policy"}: ${truth.expected_policy_id}`);
  if (truth.expected_eligible !== undefined && truth.expected_eligible !== null) lines.push(`${language === "zh" ? "符合资格" : "Eligible"}: ${truth.expected_eligible}`);
  if (truth.expected_gift !== undefined && truth.expected_gift !== null) lines.push(`${language === "zh" ? "赠品" : "Gift"}: ${truth.expected_gift}`);
  if (truth.expected_error) lines.push(language === "zh" ? "预期错误：是" : "Expected error: true");
  return lines;
}

function localizedCaseInput(value: string, language: Language): string {
  if (language !== "zh") return value;
  const eligibility = value.match(/Check gift eligibility for (POLICY_[A-Z]) on (\d{4}-\d{2}-\d{2}) with purchase amount (\d+)\./i);
  if (eligibility) return `检查 ${eligibility[2]} 支付、金额 ${eligibility[3]} 元的订单是否符合 ${eligibility[1]} 的赠品领取条件。`;
  return value;
}

function CaseDetail({ item, language }: { item: BenchmarkCase; language: Language }) {
  const lines = groundTruthSummary(item, language);
  return <div className="benchmark-detail"><div className="card-heading"><div className="heading-title"><span className="number">{item.test_case.id.replace(/\D/g, "") || "•"}</span><h2>{item.test_case.id}</h2></div><span className="status-pill muted">{language === "zh" && item.test_case.difficulty === "easy" ? "简单" : item.test_case.difficulty}</span></div><div className="rail-row"><span>{t(language, "categoryLabel")}</span><b>{language === "zh" && item.test_case.category === "normal" ? "常规" : item.test_case.category}</b></div><div className="benchmark-field"><small>{t(language, "requestLabel")}</small><p>{localizedCaseInput(item.test_case.input, language)}</p></div><div className="benchmark-field"><small>{t(language, "purposeLabel")}</small><p>{item.test_case.requirement_ids.join(", ") || t(language, "noDetails")}</p></div><div className="benchmark-field"><small>{t(language, "groundTruthLabel")}</small>{lines.map(line => <p key={line}>{line}</p>)}</div></div>;
}

export default function BenchmarksPage() {
  const [data, setData] = useState<BenchmarkResponse | null>(null);
  const [selected, setSelected] = useState<BenchmarkCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { fetchBenchmarks().then(result => { setData(result); setSelected(result.fixed_regression[0] ?? null); }).catch(reason => setError(reason instanceof Error ? reason.message : String(reason))); }, []);
  return <RouteShell>{language => <section className="card benchmark-page"><div className="card-heading"><div className="heading-title"><span className="number">▦</span><h2>{t(language, "benchmarkTitle")} / Coverage</h2></div><span className="status-pill muted">{data ? t(language, "available") : "…"}</span></div><p className="muted-text">{language === "zh" ? "我们测过什么，以及哪些行为边界仍需探索。" : "What has been tested, and which behavior boundaries remain unexplored."}</p>{error && <div className="error-box">{error}</div>}{!data && !error && <div className="empty-execution"><b>{t(language, "notConnected")}</b></div>}{data && <><div className="benchmark-groups">{groups.map(([key, titleKey, bodyKey], index) => <section className="benchmark-group" key={key}><h3><span className="coverage-kind">{["Regression", "Adaptive", "Exploratory"][index]}</span>{t(language, titleKey)} <small>({data[key].length})</small></h3><p>{t(language, bodyKey)}</p><div className="case-pills">{data[key].map(item => <button className={selected?.test_case.id === item.test_case.id ? "selected" : ""} key={item.test_case.id} onClick={() => setSelected(item)}>{item.test_case.id}</button>)}</div></section>)}</div>{selected && <CaseDetail item={selected} language={language} />}</>}</section>}</RouteShell>;
}
