import type { Metadata } from "next";
import type { ReactNode } from "react";

import AuthShell from "@/components/AuthShell";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI 文章生成與自動發布 SaaS",
  description: "前後端分離 MVP",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>
        <AuthShell>{children}</AuthShell>
      </body>
    </html>
  );
}
