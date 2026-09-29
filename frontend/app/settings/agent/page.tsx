"use client";

import { RouteShell } from "../../../components/route-shell";
import { InfoPage, ReadOnlyRow } from "../../../components/info-page";
import { t } from "../../../i18n";

export default function AgentSettingsPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="config"><div className="rail-card"><span className="status-pill muted">{t(language, "readOnly")}</span><ReadOnlyRow language={language} labelKey="targetAgentLabel" value="Commerce Agent" /><ReadOnlyRow language={language} labelKey="agentVersionLabel" value="commerce-v1" /><ReadOnlyRow language={language} labelKey="systemPromptLabel" value={language === "zh" ? "负责将用户请求路由到正确的 Commerce 工具" : "Routes user requests to the correct Commerce tool"} /><ReadOnlyRow language={language} labelKey="toolDescriptionLabel" value={language === "zh" ? "商品查询 / 促销政策查询 / 赠品资格检查" : "Product lookup / promotion policy / gift eligibility"} /><ReadOnlyRow language={language} labelKey="contextLabel" value={language === "zh" ? "本地商品目录与促销政策" : "Local catalogue and promotion policies"} /><ReadOnlyRow language={language} labelKey="workflowConfigLabel" value={language === "zh" ? "最大执行步数：2" : "Maximum execution steps: 2"} /><p className="muted-text">{t(language, "allowedHarnessLabel")}: system_prompt, tool_description, context, workflow_config</p></div></InfoPage>}</RouteShell>;
}
