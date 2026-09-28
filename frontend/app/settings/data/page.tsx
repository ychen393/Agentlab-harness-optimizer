"use client";

import { RouteShell } from "../../../components/route-shell";
import { InfoPage } from "../../../components/info-page";
import { t } from "../../../i18n";

export default function DataPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="dataTitle"><p className="muted-text">{t(language, "mvpDataMessage")}</p><div className="details">{t(language, "fixtureSource")}</div></InfoPage>}</RouteShell>;
}
