import Link from "next/link";

const pages = [
  { href: "/today", label: "今日简报" },
  { href: "/history", label: "历史简报" },
  { href: "/library", label: "信息库" },
  { href: "/following", label: "我的关注" },
  { href: "/admin/sources", label: "来源管理" },
  { href: "/admin/jobs", label: "任务日志" },
  { href: "/admin/llm", label: "LLM 设置" },
  { href: "/admin/users", label: "用户管理" }
];

export default function HomePage() {
  return (
    <main className="shell">
      <section className="panel">
        <p className="eyebrow">Daily News</p>
        <h1>AI 热点信息每日汇总 Web 看板</h1>
        <p className="description">
          工程骨架已就绪。后续页面会按产品原型接入真实 API、认证和个性化规则。
        </p>
        <nav className="linkGrid" aria-label="页面入口">
          {pages.map((page) => (
            <Link key={page.href} href={page.href}>
              {page.label}
            </Link>
          ))}
        </nav>
      </section>
    </main>
  );
}
