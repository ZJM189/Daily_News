"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Bookmark,
  BrainCircuit,
  CalendarClock,
  ChevronUp,
  Database,
  History,
  ListChecks,
  LogIn,
  LogOut,
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
import RadarMark from "./RadarMark";
import { AppFooter } from "./AppFooter";
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
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);
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
    setAccountMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!accountMenuOpen) return;

    function handlePointerDown(event: PointerEvent) {
      if (!accountMenuRef.current?.contains(event.target as Node)) {
        setAccountMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setAccountMenuOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [accountMenuOpen]);

  async function handleLogout() {
    setAccountMenuOpen(false);
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
  const activeNavItem = findActiveNavItem(pathname);

  return (
    <div
      className={`appFrame ${adminRoute ? "adminFrame" : "workspaceFrame"} ${
        sidebarCollapsed ? "sidebarCollapsed" : ""
      } ${
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

        <div className="sidebarAccount" ref={accountMenuRef}>
          {accountMenuOpen ? (
            <div className="sidebarAccountMenu" role="menu">
              <div className="sidebarAccountDetails">
                <strong>{user?.display_name || user?.username}</strong>
                <span>{user?.email || user?.username}</span>
              </div>
              <button
                className="sidebarAccountAction"
                type="button"
                role="menuitem"
                onClick={() => void handleLogout()}
              >
                <LogOut size={16} />
                <span>退出登录</span>
              </button>
            </div>
          ) : null}
          <button
            className="sidebarFooter"
            type="button"
            aria-label="打开账号菜单"
            aria-haspopup="menu"
            aria-expanded={accountMenuOpen}
            title="打开账号菜单"
            onClick={() => setAccountMenuOpen((open) => !open)}
          >
            <span className="sidebarAvatar" aria-hidden="true">
              {userInitial(user)}
            </span>
            <span className="sidebarUserText">
              <strong>{user?.display_name || user?.username}</strong>
              <small>{user?.role === "admin" ? "管理员" : "普通用户"}</small>
            </span>
            <ChevronUp className="sidebarAccountChevron" size={16} aria-hidden="true" />
          </button>
        </div>
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
          <div className="topbarContext">
            <strong>{activeNavItem.label}</strong>
            <span>{activeNavItem.description}</span>
          </div>
        </header>
        <FavoritesProvider key={user?.id}>
          {guardedChildren}
          {adminRoute ? null : <LibraryChatWidget />}
        </FavoritesProvider>
        <AppFooter />
        {adminRoute ? null : <MobileBottomNav pathname={pathname} />}
      </div>
    </div>
  );
}

function MobileBottomNav({ pathname }: { pathname: string }) {
  return (
    <nav className="mobileBottomNav" aria-label="主工作区快捷导航">
      {primaryNav.map((item) => {
        const Icon = item.icon;
        const active = isNavItemActive(pathname, item.href);
        return (
          <Link
            className={`mobileBottomNavLink ${active ? "active" : ""}`}
            href={item.href}
            key={item.href}
            aria-current={active ? "page" : undefined}
          >
            <Icon size={20} strokeWidth={2.1} aria-hidden="true" />
            <span>{mobileNavLabel(item.label)}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarGroup({ title, items, pathname }: { title: string; items: NavItem[]; pathname: string }) {
  return (
    <div className="navGroup">
      <p className="navGroupTitle">{title}</p>
      {items.map((item) => {
        const Icon = item.icon;
        const active = isNavItemActive(pathname, item.href);
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

function findActiveNavItem(pathname: string) {
  return (
    [...primaryNav, ...adminNav].find((item) => isNavItemActive(pathname, item.href)) ??
    primaryNav[0]
  );
}

function isNavItemActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function mobileNavLabel(label: string) {
  if (label === "今日 AI 简报") return "今日";
  return label.replace(/^我的/, "").replace(/简报$/, "");
}

function userInitial(user: User | null) {
  const name = user?.display_name || user?.username || "U";
  return name.slice(0, 1).toUpperCase();
}

function isPublicRoute(pathname: string) {
  return publicRoutes.has(pathname);
}

function GitHubMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 98 96"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="currentColor"
        fillRule="evenodd"
        clipRule="evenodd"
        d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.669 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.303.89 2.852 3.316 2.363 19.412-6.52 33.405-24.935 33.405-46.69C97.707 22 75.788 0 48.854 0z"
      />
    </svg>
  );
}

function PublicShell({ children, pathname }: { children: React.ReactNode; pathname: string }) {
  const nextPath = pathname === "/" ? "/today" : pathname;
  const loginHref = `/login?next=${encodeURIComponent(nextPath)}`;

  return (
    <div className="publicFrame">
      <header className="publicTopbar">
        <div className="publicTopbarInner">
          <nav className="publicNav" aria-label="公开导航">
            <Link className={pathname === "/" || pathname === "/today" ? "active" : ""} href="/today">
              <RadarMark />
              每日 AI 简报
            </Link>
          </nav>
          <div className="publicTopbarActions">
            <a
              className="githubBadge"
              href="https://github.com/ZJM189/Daily_News"
              target="_blank"
              rel="noreferrer"
              aria-label="在 GitHub 查看 Daily News 源码"
              title="在 GitHub 查看源码"
            >
              <GitHubMark className="githubBadgeIcon" />
              <span>GitHub</span>
            </a>
            <Link className="publicLoginButton" href={loginHref} aria-label="登录进入工作区">
              <LogIn size={15} aria-hidden="true" />
              <span>登录进入工作区</span>
            </Link>
          </div>
        </div>
      </header>
      {children}
      <AppFooter />
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
