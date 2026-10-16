import type { Metadata } from "next";
import "./globals.css";
import "./typography.css";

export const metadata: Metadata = {
  title: "AgentLab — Harness Evaluation",
  description: "Observe, diagnose, repair, and validate AI Agents.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
