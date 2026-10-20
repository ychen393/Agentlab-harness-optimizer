"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Globe2 } from "lucide-react";
import { useState } from "react";
import { t } from "../i18n";
import type { Language } from "../types/contracts";

const topRoutes = [
  ["/", "home"], ["/runs", "runs"], ["/failures", "failures"], ["/patches", "patches"], ["/regression", "regression"],
] as const;

export function RouteShell({ children }: { children: (language: Language) => React.ReactNode }) {
  const pathname = usePathname();
  const [language, setLanguage] = useState<Language>("zh");
  const item = (icon: string, label: string, href: string, disabled = false) => disabled ? <span className="side-item disabled" title={t(language, "unsupportedStatus")}><span>{icon}</span>{label}<small>{t(language, "unsupportedStatus")}</small></span> : href.includes("?") ? <a className="side-item" href={href}><span>{icon}</span>{label}</a> : <Link className={`side-item ${pathname === href ? "selected" : ""}`} href={href}><span>{icon}</span>{label}</Link>;
  return <div className="app-shell">
    <header className="topbar"><Link className="brand" href="/"><div className="brand-mark">A</div><div><strong>AgentLab</strong><small>{t(language, "brandTagline")}</small></div></Link><nav className="topnav">{topRoutes.map(([href, key]) => <Link className={pathname === href ? "active" : ""} href={href} key={href}>{t(language, key)}</Link>)}</nav><div className="top-actions"><span className="select-pill">◉　{t(language, "target")}: <b>Commerce Agent</b></span><span className="select-pill">⚙　{t(language, "environment")}: <b>Demo</b></span><Globe2 size={21} color="#172554" /><div className="language"><button className={language === "zh" ? "selected" : ""} onClick={() => setLanguage("zh")}>中文</button><button className={language === "en" ? "selected" : ""} onClick={() => setLanguage("en")}>EN</button></div><div className="avatar">Y</div></div></header>
    <aside className="sidebar"><div className="side-main">{item("⌂", t(language, "home"), "/")}{item("✦", t(language, "quickStart"), "/")}</div><section className="side-section"><h4>{t(language, "templates")}</h4>{item("◈", t(language, "promo"), "/?template=promo")}{item("▣", t(language, "product"), "/?template=product")}{item("⌘", t(language, "toolContractRepair"), "/?template=tool-contract")}{item("▤", t(language, "order"), "/?template=order", true)}{item("▱", t(language, "returns"), "/?template=returns", true)}{item("□", t(language, "custom"), "/?template=custom")}</section><section className="side-section"><h4>{t(language, "settings")}</h4>{item("✣", t(language, "config"), "/settings/agent")}{item("▦", t(language, "tests"), "/settings/benchmarks")}{item("✓", t(language, "evaluator"), "/settings/evaluator")}{item("▤", t(language, "data"), "/settings/data")}</section><div className="sidebar-note"><b>AgentLab</b><span>{t(language, "sidebarNote")}</span></div></aside>
    <main className="main">{children(language)}</main>
  </div>;
}
