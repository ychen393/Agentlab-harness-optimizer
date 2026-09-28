"use client";

import { t, type TranslationKey } from "../i18n";
import type { Language } from "../types/contracts";

export function InfoPage({ language, titleKey, emptyKey, children }: { language: Language; titleKey: TranslationKey; emptyKey?: TranslationKey; children?: React.ReactNode }) {
  return <section className="card"><div className="card-heading"><div className="heading-title"><span className="number">•</span><h2>{t(language, titleKey)}</h2></div><span className="status-pill muted">{children ? t(language, "available") : t(language, "notConnected")}</span></div>{children ?? <div className="empty-execution"><div><b>{emptyKey ? t(language, emptyKey) : t(language, "notConnected")}</b></div></div>}</section>;
}

export function ReadOnlyRow({ language, labelKey, value }: { language: Language; labelKey: TranslationKey; value: string }) {
  return <div className="rail-row"><span>{t(language, labelKey)}</span><code>{value}</code></div>;
}
