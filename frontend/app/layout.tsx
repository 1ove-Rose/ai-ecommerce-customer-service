import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart CS Console",
  description: "电商客服多 Agent 工作台",
};

const navItems = [
  { href: "/chat", label: "客服聊天" },
  { href: "/orders", label: "订单查询" },
  { href: "/tickets", label: "工单售后" },
  { href: "/logs", label: "工具日志" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <div className="brand">
              <span className="brandMark">CS</span>
              <div>
                <strong>Smart CS</strong>
                <small>电商客服多 Agent</small>
              </div>
            </div>
            <nav className="nav">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}