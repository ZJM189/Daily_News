"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bell,
  Bookmark,
  BrainCircuit,
  CalendarClock,
  Database,
  History,
  ListChecks,
  Menu,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  Rss,
  ShieldAlert,
  Users
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { apiPost, getCurrentUser } from "../../lib/api";
import type { User } from "../../lib/types";
import { FavoritesProvider } from "./FavoritesProvider";
import { LibraryChatWidget } from "./LibraryChatWidget";

type NavItem = {
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
};

const primaryNav: NavItem[] = [
  { href: "/today", label: "今日 AI 简报", description: "当天精选", icon: Newspaper },
  { href: "/history", label: "历史简报", description: "按天回溯", icon: History },
  { href: "/library", label: "信息库", description: "全量检索", icon: Database },
  { href: "/following", label: "我的关注", description: "个性化流", icon: Bell },
  { href: "/favorites", label: "我的收藏", description: "保存的内容", icon: Bookmark }
];

const adminNav: NavItem[] = [
  { href: "/admin/jobs", label: "任务日志", description: "进度与失败", icon: ListChecks },
  { href: "/admin/scheduler", label: "调度配置", description: "定时任务", icon: CalendarClock },
  { href: "/admin/sources", label: "来源管理", description: "采集源", icon: Rss },
  { href: "/admin/llm", label: "LLM 设置", description: "模型服务", icon: BrainCircuit },
  { href: "/admin/users", label: "用户管理", description: "账号权限", icon: Users }
];

const publicRoutes = new Set(["/", "/today", "/login"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!isPublicRoute(pathname));
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const publicRoute = isPublicRoute(pathname);
  const loginRoute = pathname === "/login";
  const adminRoute = pathname.startsWith("/admin");

  useEffect(() => {
    let active = true;
    const currentPublicRoute = isPublicRoute(pathname);
    if (pathname === "/login") {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(!currentPublicRoute);
    getCurrentUser()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        if (!currentPublicRoute) {
          const nextPath =
            typeof window === "undefined"
              ? pathname
              : `${window.location.pathname}${window.location.search}`;
          router.replace(`/login?next=${encodeURIComponent(nextPath)}`);
        }
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

  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname]);

  async function handleLogout() {
    await apiPost("/api/v1/auth/logout");
    setUser(null);
    router.replace("/login");
  }

  if (loginRoute) {
    return <>{children}</>;
  }

  if (loading && !publicRoute) {
    return (
      <main className="appLoading">
        <div className="spinner" />
        <span>正在进入看板</span>
      </main>
    );
  }

  if (!user && !publicRoute) {
    return (
      <main className="appLoading">
        <div className="spinner" />
        <span>正在跳转登录</span>
      </main>
    );
  }

  if (!user) {
    return <PublicShell pathname={pathname}>{children}</PublicShell>;
  }

  const guardedChildren = adminRoute && user.role !== "admin" ? <AccessDenied /> : children;

  return (
    <div
      className={`appFrame ${sidebarCollapsed ? "sidebarCollapsed" : ""} ${
        mobileSidebarOpen ? "mobileSidebarOpen" : ""
      }`}
    >
      <button
        className="sidebarOverlay"
        type="button"
        aria-label="关闭侧边栏"
        onClick={() => setMobileSidebarOpen(false)}
      />
      <aside className="sidebar" aria-label="应用侧边栏">
        <div className="sidebarHeader">
          <Link href="/today" className="brandBlock" aria-label="Daily News 首页">
            <span className="brandMark">DN</span>
            <span className="brandText">
              <strong>Daily News</strong>
              <small>AI 热点看板</small>
            </span>
          </Link>
          <button
            className="sidebarIconButton sidebarCollapseButton"
            type="button"
            aria-label={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
            title={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
            onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
          >
            {sidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        <nav className="sideNav" aria-label="主导航">
          <SidebarGroup title="主工作区" items={primaryNav} pathname={pathname} />
          {user?.role === "admin" ? (
            <SidebarGroup title="系统管理" items={adminNav} pathname={pathname} />
          ) : null}
        </nav>

        <footer className="sidebarFooter">
          <span className="sidebarAvatar" aria-hidden="true">
            {userInitial(user)}
          </span>
          <span className="sidebarUserText">
            <strong>{user?.display_name || user?.username}</strong>
            <small>{user?.role === "admin" ? "管理员" : "普通用户"}</small>
          </span>
        </footer>
      </aside>
      <div className="contentColumn">
        <header className="topbar">
          <button
            className="ghostButton mobileSidebarButton"
            type="button"
            onClick={() => setMobileSidebarOpen(true)}
          >
            <Menu size={17} />
            <span>菜单</span>
          </button>
          <div className="topbarUserActions">
            <div>
              <strong>{user?.display_name || user?.username}</strong>
              <span>{user?.role === "admin" ? "管理员" : "普通用户"}</span>
            </div>
            <button className="ghostButton" type="button" onClick={() => void handleLogout()}>
              退出
            </button>
          </div>
        </header>
        <FavoritesProvider key={user?.id}>
          {guardedChildren}
          <LibraryChatWidget />
        </FavoritesProvider>
      </div>
    </div>
  );
}

function SidebarGroup({ title, items, pathname }: { title: string; items: NavItem[]; pathname: string }) {
  return (
    <div className="navGroup">
      <p className="navGroupTitle">{title}</p>
      {items.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebarLink ${active ? "active" : ""}`}
            title={item.label}
          >
            <span className="sidebarLinkIcon" aria-hidden="true">
              <Icon size={18} strokeWidth={2.1} />
            </span>
            <span className="sidebarLinkText">
              <strong>{item.label}</strong>
              <small>{item.description}</small>
            </span>
          </Link>
        );
      })}
    </div>
  );
}

function userInitial(user: User | null) {
  const name = user?.display_name || user?.username || "U";
  return name.slice(0, 1).toUpperCase();
}

function isPublicRoute(pathname: string) {
  return publicRoutes.has(pathname);
}

function PublicShell({ children, pathname }: { children: React.ReactNode; pathname: string }) {
  const nextPath = pathname === "/" ? "/today" : pathname;
  const loginHref = `/login?next=${encodeURIComponent(nextPath)}`;

  return (
    <div className="publicFrame">
      <header className="publicTopbar">
        <Link href="/" className="publicBrand" aria-label="Daily News 公开首页">
          <span className="publicBrandOrb">DN</span>
          <span>
            <strong>Daily News</strong>
            <small>AI BRIEFING</small>
          </span>
        </Link>
        <nav className="publicNav" aria-label="公开导航">
          <Link className={pathname === "/" || pathname === "/today" ? "active" : ""} href="/today">
            今日 AI 简报
          </Link>
        </nav>
        <Link className="publicLoginButton" href={loginHref}>
          登录进入工作区
        </Link>
      </header>
      {children}
    </div>
  );
}

function AccessDenied() {
  return (
    <main className="pageSurface pageScaffold">
      <section className="surfaceCard accessDeniedPanel">
        <div className="emptyIcon">
          <ShieldAlert size={24} />
        </div>
        <h1>无权访问系统管理</h1>
        <p className="mutedText">当前账号没有管理员权限，可以继续查看今日 AI 简报、历史简报和信息库内容。</p>
        <Link className="linkButton compactLink" href="/today">
          返回今日 AI 简报
        </Link>
      </section>
    </main>
  );
}
