"use client";

import { useEffect, useState } from "react";
import { RouteShell } from "../../components/route-shell";
import { fetchRuns, type SessionRun } from "../../lib/api";
import { t } from "../../i18n";

export default function RunsPage() {
  const [runs, setRuns] = useState<SessionRun[]>([]);
  useEffect(() => { fetchRuns().then(result => setRuns(result.runs)).catch(() => setRuns([])); }, []);
  return <RouteShell>{language => <section className="card"><div className="card-heading"><div className="heading-title"><span className="number">•</span><h2>{t(language, "runHistoryTitle")}</h2></div><span className="status-pill muted">{t(language, "currentSession")}</span></div>{runs.length === 0 ? <div className="empty-execution"><b>{t(language, "emptyRunHistory")}</b><p>{t(language, "emptyRunHistoryBody")}</p></div> : <div className="history-list">{runs.map(run => <details className="history-item" key={run.run_id}><summary><b>{run.run_id}</b><span>{run.execution_status === "failed" ? t(language, "executionFailed") : t(language, "executionCompleted")} · {run.evaluation_status === "pass" ? t(language, "pass") : run.evaluation_status === "fail" ? t(language, "fail") : t(language, "notEvaluated")}</span></summary><p>{run.request}</p><small>{run.created_at} · {run.scenario_id ?? t(language, "customScenario")} · {run.agent_version}</small></details>)}</div>}</section>}</RouteShell>;
}
