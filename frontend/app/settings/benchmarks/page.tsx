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
  if (truth.expected_policy_id) lines.push(`policy: ${truth.expected_policy_id}`);
  if (truth.expected_eligible !== undefined && truth.expected_eligible !== null) lines.push(`eligible: ${truth.expected_eligible}`);
  if (truth.expected_gift !== undefined && truth.expected_gift !== null) lines.push(`gift: ${truth.expected_gift}`);
  if (truth.expected_error) lines.push("expected error: true");
  return lines;
}

function CaseDetail({ item, language }: { item: BenchmarkCase; language: Language }) {
  const lines = groundTruthSummary(item, language);
  return <div className="benchmark-detail"><div className="card-heading"><div className="heading-title"><span className="number">{item.test_case.id.replace(/\D/g, "") || "•"}</span><h2>{item.test_case.id}</h2></div><span className="status-pill muted">{item.test_case.difficulty}</span></div><div className="rail-row"><span>{t(language, "categoryLabel")}</span><b>{item.test_case.category}</b></div><div className="benchmark-field"><small>{t(language, "requestLabel")}</small><p>{item.test_case.input}</p></div><div className="benchmark-field"><small>{t(language, "purposeLabel")}</small><p>{item.test_case.requirement_ids.join(", ") || t(language, "noDetails")}</p></div><div className="benchmark-field"><small>{t(language, "groundTruthLabel")}</small>{lines.map(line => <p key={line}>{line}</p>)}</div></div>;
}

export default function BenchmarksPage() {
  const [data, setData] = useState<BenchmarkResponse | null>(null);
  const [selected, setSelected] = useState<BenchmarkCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { fetchBenchmarks().then(result => { setData(result); setSelected(result.fixed_regression[0] ?? null); }).catch(reason => setError(reason instanceof Error ? reason.message : String(reason))); }, []);
  return <RouteShell>{language => <section className="card benchmark-page"><div className="card-heading"><div className="heading-title"><span className="number">▦</span><h2>{t(language, "benchmarkTitle")}</h2></div><span className="status-pill muted">{data ? t(language, "available") : "…"}</span></div><p className="muted-text">{t(language, "benchmarkSelect")}</p>{error && <div className="error-box">{error}</div>}{!data && !error && <div className="empty-execution"><b>{t(language, "notConnected")}</b></div>}{data && <><div className="benchmark-groups">{groups.map(([key, titleKey, bodyKey]) => <section className="benchmark-group" key={key}><h3>{t(language, titleKey)} <small>({data[key].length})</small></h3><p>{t(language, bodyKey)}</p><div className="case-pills">{data[key].map(item => <button className={selected?.test_case.id === item.test_case.id ? "selected" : ""} key={item.test_case.id} onClick={() => setSelected(item)}>{item.test_case.id}</button>)}</div></section>)}</div>{selected && <CaseDetail item={selected} language={language} />}</>}</section>}</RouteShell>;
}
