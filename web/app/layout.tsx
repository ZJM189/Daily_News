import type { Metadata } from "next";
import "@fontsource-variable/noto-sans-sc";
import { AppShell } from "./components/AppShell";
import "./globals.css";
import "./favorites.css";

export const metadata: Metadata = {
  title: "Daily News",
  description: "AI 热点信息每日汇总 Web 看板"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
