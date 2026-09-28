"use client";

import { RouteShell } from "../../components/route-shell";
import { InfoPage } from "../../components/info-page";

export default function FailuresPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="failureAnalysisTitle" emptyKey="emptyFailureAnalysis" />}</RouteShell>;
}
