"use client";

import { RouteShell } from "../../../components/route-shell";
import { InfoPage, ReadOnlyRow } from "../../../components/info-page";
import { t } from "../../../i18n";

export default function EvaluatorPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="evaluatorTitle"><div className="rail-card"><h3>{language === "zh" ? "独立评估器" : "Independent evaluator"}</h3><p>{language === "zh" ? "在不修改 Ground Truth 的情况下判断 Agent 是否正确完成任务。" : "Judges task correctness without modifying Ground Truth."}</p><ReadOnlyRow language={language} labelKey="activeEvaluator" value="Commerce deterministic evaluator" /><ReadOnlyRow language={language} labelKey="targetAgentLabel" value="Commerce Agent" /><ReadOnlyRow language={language} labelKey="evaluationChecks" value={language === "zh" ? "任务执行、工具调用、调用顺序、促销政策、资格判断、赠品结果" : "Execution, tool calls, sequence, policy, eligibility, gift"} /><p className="muted-text">{t(language, "readOnly")}</p></div></InfoPage>}</RouteShell>;
}
