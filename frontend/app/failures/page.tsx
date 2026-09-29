"use client";

import { useEffect, useState } from "react";
import { RouteShell } from "../../components/route-shell";
import { fetchFailures } from "../../lib/api";
import { t } from "../../i18n";

export default function FailuresPage() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof fetchFailures>>["failures"]>([]);
  useEffect(() => { fetchFailures().then(result => setItems(result.failures)).catch(() => setItems([])); }, []);
  return <RouteShell>{language => <section className="card"><h2>{t(language, "failureAnalysisTitle")}</h2>{items.length === 0 ? <div className="empty-execution"><b>{t(language, "emptyFailureAnalysis")}</b></div> : items.map(item => <article className="history-item" key={item.run_id}><b>{item.failure_pattern.category === "workflow_step_limit" ? t(language, "workflowFailureHuman") : item.failure_pattern.category}</b><p>{item.root_cause.root_cause}</p><small>{t(language, "affected")}: {item.failure_pattern.affected_test_ids.join(", ")} · {t(language, "runId")}: {item.run_id}</small></article>)}</section>}</RouteShell>;
}
