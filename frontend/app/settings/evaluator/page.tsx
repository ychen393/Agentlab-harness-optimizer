"use client";

import { RouteShell } from "../../../components/route-shell";
import { InfoPage, ReadOnlyRow } from "../../../components/info-page";
import { t } from "../../../i18n";

export default function EvaluatorPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="evaluatorTitle"><div className="rail-card"><ReadOnlyRow language={language} labelKey="activeEvaluator" value="Commerce deterministic evaluator" /><ReadOnlyRow language={language} labelKey="targetAgentLabel" value="Commerce Agent" /><ReadOnlyRow language={language} labelKey="evaluationChecks" value="execution, tool sequence, policy, eligibility, gift" /><p className="muted-text">{t(language, "readOnly")}</p></div></InfoPage>}</RouteShell>;
}
