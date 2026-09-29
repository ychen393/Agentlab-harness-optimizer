"use client";

import { RouteShell } from "../../../components/route-shell";
import { InfoPage } from "../../../components/info-page";
import { t } from "../../../i18n";
import { useEffect, useState } from "react";
import { fetchBenchmarks } from "../../../lib/api";

export default function DataPage() {
  const [counts, setCounts] = useState({ fixed: 7, adaptive: 5, coverage: 4 });
  useEffect(() => { fetchBenchmarks().then(data => setCounts({ fixed: data.fixed_regression.length, adaptive: data.adaptive_challenges.length, coverage: data.coverage_exploration.length })).catch(() => undefined); }, []);
  return <RouteShell>{language => <InfoPage language={language} titleKey="dataTitle"><p className="muted-text">{t(language, "mvpDataMessage")}</p><div className="rail-row"><span>{language === "zh" ? "商品目录" : "Catalogue"}</span><b>3 {language === "zh" ? "个商品" : "products"}</b></div><div className="rail-row"><span>{language === "zh" ? "促销政策" : "Promotion policies"}</span><b>2 {language === "zh" ? "条政策" : "policies"}</b></div><div className="rail-row"><span>{t(language, "fixedRegression")}</span><b>{counts.fixed} {language === "zh" ? "个案例" : "cases"}</b></div><div className="rail-row"><span>{t(language, "adaptiveChallenges")}</span><b>{counts.adaptive} {language === "zh" ? "个案例" : "cases"}</b></div><div className="rail-row"><span>{t(language, "coverageExploration")}</span><b>{counts.coverage} {language === "zh" ? "个案例" : "cases"}</b></div><div className="details">{language === "zh" ? "这些数据构成当前 Commerce MVP 的受控测试环境。" : "These data form the controlled Commerce MVP test environment."}</div></InfoPage>}</RouteShell>;
}
