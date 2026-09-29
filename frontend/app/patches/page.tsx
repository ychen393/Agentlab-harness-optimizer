"use client";

import { useEffect, useState } from "react";
import { RouteShell } from "../../components/route-shell";
import { fetchPatches } from "../../lib/api";
import { t } from "../../i18n";

export default function PatchesPage() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof fetchPatches>>["patches"]>([]);
  useEffect(() => { fetchPatches().then(result => setItems(result.patches)).catch(() => setItems([])); }, []);
  return <RouteShell>{language => <section className="card"><h2>{t(language, "patchManagementTitle")}</h2>{items.length === 0 ? <div className="empty-execution"><b>{t(language, "emptyPatchManagement")}</b></div> : items.map(item => <article className="history-item" key={item.run_id}><b>{item.patch.target_component}</b><p>{JSON.stringify(item.patch.old_value)} → {JSON.stringify(item.patch.proposed_value)}</p><small>{t(language, "runId")}: {item.run_id}<br/>{item.patch.reason}</small></article>)}</section>}</RouteShell>;
}
