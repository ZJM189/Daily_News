import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowRight, BookOpen, Rss, Settings, Star } from "lucide-react";
import { PageHeader, PageScaffold } from "./components/UiPrimitives";

export default function HomePage() {
  return (
    <PageScaffold>
      <PageHeader
        eyebrow="AI 热点看板"
        title="从采集到简报的工作台"
        description="每天抓取 AI 热点内容，经过标准化、评分、专题合并和中文摘要后，生成可阅读的今日简报。"
        actions={
          <Link className="linkButton" href="/today">
            查看今日简报
            <ArrowRight size={16} />
          </Link>
        }
      />

      <section className="quickStartGrid">
        <QuickStartCard
          icon={<Settings size={20} />}
          title="首次配置"
          description="配置 RSS、GitHub、arXiv 等来源，以及 OpenAI 兼容 LLM。"
          href="/admin/sources"
          action="管理来源"
        />
        <QuickStartCard
          icon={<Rss size={20} />}
          title="生成简报"
          description="一键执行抓取、整理、评分、合并、摘要和发布。"
          href="/admin/jobs"
          action="打开任务日志"
        />
        <QuickStartCard
          icon={<BookOpen size={20} />}
          title="复核内容"
          description="在全量信息库里按关键词、来源、分类和分数检索。"
          href="/library"
          action="进入信息库"
        />
        <QuickStartCard
          icon={<Star size={20} />}
          title="个性化关注"
          description="设置偏好关键词、分类和屏蔽规则，得到个人关注流。"
          href="/following"
          action="设置我的关注"
        />
      </section>
    </PageScaffold>
  );
}

function QuickStartCard({
  icon,
  title,
  description,
  href,
  action
}: {
  icon: ReactNode;
  title: string;
  description: string;
  href: string;
  action: string;
}) {
  return (
    <Link className="quickStartCard" href={href}>
      <span className="quickStartIcon">{icon}</span>
      <strong>{title}</strong>
      <span>{description}</span>
      <em>{action}</em>
    </Link>
  );
}
