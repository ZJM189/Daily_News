import Link from "next/link";

export default function HomePage() {
  return (
    <main className="pageSurface">
      <section className="pageHeader">
        <div>
          <p className="eyebrow">AI 热点看板</p>
          <h1>从采集到简报的工作台</h1>
          <p className="description">
            每天抓取 AI 热点内容，经过标准化、评分、专题合并和中文摘要后，生成可阅读的今日简报。
          </p>
        </div>
        <Link className="linkButton" href="/today">
          查看今日简报
        </Link>
      </section>

      <section className="quickStartGrid">
        <QuickStartCard
          title="首次配置"
          description="配置 RSS、GitHub、arXiv 等来源，以及 OpenAI 兼容 LLM。"
          href="/admin/sources"
          action="管理来源"
        />
        <QuickStartCard
          title="生成简报"
          description="一键执行抓取、整理、评分、合并、摘要和发布。"
          href="/admin/jobs"
          action="打开任务日志"
        />
        <QuickStartCard
          title="复核内容"
          description="在全量信息库里按关键词、来源、分类和分数检索。"
          href="/library"
          action="进入信息库"
        />
        <QuickStartCard
          title="个性化关注"
          description="设置偏好关键词、分类和屏蔽规则，得到个人关注流。"
          href="/following"
          action="设置我的关注"
        />
      </section>
    </main>
  );
}

function QuickStartCard({
  title,
  description,
  href,
  action
}: {
  title: string;
  description: string;
  href: string;
  action: string;
}) {
  return (
    <Link className="quickStartCard" href={href}>
      <strong>{title}</strong>
      <span>{description}</span>
      <em>{action}</em>
    </Link>
  );
}
