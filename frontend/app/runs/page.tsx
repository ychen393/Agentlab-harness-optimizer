"use client";

import { RouteShell } from "../../components/route-shell";
import { InfoPage } from "../../components/info-page";
import { t } from "../../i18n";

export default function RunsPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="runHistoryTitle" emptyKey="emptyRunHistory"><p className="muted-text">{t(language, "runHistoryTitle")}</p></InfoPage>}</RouteShell>;
}
