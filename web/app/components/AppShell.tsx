"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiPost, getCurrentUser } from "../../lib/api";
import type { User } from "../../lib/types";

const primaryNav = [
  { href: "/today", label: "今日简报" },
  { href: "/history", label: "历史简报" },
  { href: "/library", label: "信息库" },
  { href: "/following", label: "我的关注" }
];

const adminNav = [
  { href: "/admin/jobs", label: "任务日志" },
  { href: "/admin/scheduler", label: "调度配置" },
  { href: "/admin/sources", label: "来源管理" },
  { href: "/admin/llm", label: "LLM 设置" },
  { href: "/admin/users", label: "用户管理" }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(pathname !== "/login");

  useEffect(() => {
    let active = true;
    if (pathname === "/login") {
      setLoading(false);
      return;
    }
    getCurrentUser()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        router.replace("/login");
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [pathname, router]);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <main className="appLoading">
        <div className="spinner" />
        <span>正在进入看板</span>
      </main>
    );
  }

  return (
    <div className="appFrame">
      <aside className="sidebar">
        <Link href="/today" className="brandBlock">
          <span className="brandMark">DN</span>
          <span>
            <strong>Daily News</strong>
            <small>AI 热点看板</small>
          </span>
        </Link>
        <nav className="sideNav" aria-label="主导航">
          <div className="navGroup">
            <p className="navGroupTitle">主工作区</p>
            {primaryNav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={pathname === item.href ? "active" : ""}
              >
                {item.label}
              </Link>
            ))}
          </div>
          {user?.role === "admin" ? (
            <div className="navGroup">
              <p className="navGroupTitle">系统管理</p>
              {adminNav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={pathname === item.href ? "active" : ""}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          ) : null}
        </nav>
      </aside>
      <div className="contentColumn">
        <header className="topbar">
          <div>
            <strong>{user?.display_name || user?.username}</strong>
            <span>{user?.role === "admin" ? "管理员" : "普通用户"}</span>
          </div>
          <button
            className="ghostButton"
            type="button"
            onClick={async () => {
              await apiPost("/api/v1/auth/logout");
              router.replace("/login");
            }}
          >
            退出
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}
