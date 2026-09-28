"use client";

import { RouteShell } from "../../components/route-shell";
import { InfoPage } from "../../components/info-page";

export default function PatchesPage() {
  return <RouteShell>{language => <InfoPage language={language} titleKey="patchManagementTitle" emptyKey="emptyPatchManagement" />}</RouteShell>;
}
