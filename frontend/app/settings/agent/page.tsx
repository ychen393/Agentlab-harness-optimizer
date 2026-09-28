"use client";

import { RouteShell } from "../../../components/route-shell";
import { InfoPage, ReadOnlyRow } from "../../../components/info-page";
import { t } from "../../../i18n";

export default function AgentSettingsPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="config"><div className="rail-card"><span className="status-pill muted">{t(language, "readOnly")}</span><ReadOnlyRow language={language} labelKey="targetAgentLabel" value="Commerce Agent" /><ReadOnlyRow language={language} labelKey="agentVersionLabel" value="commerce-v1" /><ReadOnlyRow language={language} labelKey="systemPromptLabel" value="Configured in Commerce V1 harness" /><ReadOnlyRow language={language} labelKey="toolDescriptionLabel" value="Commerce tool contracts" /><ReadOnlyRow language={language} labelKey="contextLabel" value="Commerce policies and fixtures" /><ReadOnlyRow language={language} labelKey="workflowConfigLabel" value="max_steps: 2" /><p className="muted-text">{t(language, "allowedHarnessLabel")}: system_prompt, tool_description, context, workflow_config</p></div></InfoPage>}</RouteShell>;
}
