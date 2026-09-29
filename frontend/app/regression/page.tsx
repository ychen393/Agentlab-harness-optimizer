"use client";

import { useEffect, useState } from "react";
import { RouteShell } from "../../components/route-shell";
import { fetchRegressions } from "../../lib/api";
import { t } from "../../i18n";

export default function RegressionPage() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof fetchRegressions>>["regressions"]>([]);
  useEffect(() => { fetchRegressions().then(result => setItems(result.regressions)).catch(() => setItems([])); }, []);
  return <RouteShell>{language => <section className="card"><h2>{t(language, "regressionTitle")}</h2>{items.length === 0 ? <div className="empty-execution"><b>{t(language, "emptyRegression")}</b></div> : items.map(item => <article className="history-item" key={item.run_id}><b>{item.regression.baseline_version} → {item.regression.candidate_version}</b><p>{item.regression.baseline_pass_count} / {item.regression.baseline_total} → {item.regression.candidate_pass_count} / {item.regression.candidate_total}</p><small>{t(language, "improved")}: {item.regression.improved_test_ids.join(", ") || "—"} · {t(language, "regressions")}: {item.regression.regressed_test_ids.join(", ") || "0"}<br/>{t(language, "decision")}: {item.regression.decision.toUpperCase()}</small></article>)}</section>}</RouteShell>;
}
