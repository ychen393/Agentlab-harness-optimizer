"use client";

import { RouteShell } from "../../components/route-shell";
import { InfoPage } from "../../components/info-page";

export default function RegressionPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="regressionTitle" emptyKey="emptyRegression" />}</RouteShell>;
}
