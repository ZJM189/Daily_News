import Link from "next/link";
import { ExternalLink, FileSearch, Sparkles, TrendingUp } from "lucide-react";
import type { Digest } from "../../lib/types";
import { MetricCard, PageHeader, SurfaceCard } from "./UiPrimitives";

const categoryLabels: Record<string, string> = {
  model_company: "模型公司",
  open_source: "开源项目",
  research_paper: "研究论文",
  product_launch: "产品发布",
  community: "社区动态",
  industry_funding: "产业融资",
  other: "其他"
};

const sourceTypeLabels: Record<string, string> = {
  rss: "RSS",
  hacker_news: "Hacker News",
  github: "GitHub",
  arxiv: "arXiv",
  product_hunt: "Product Hunt",
  hugging_face: "Hugging Face"
};

export function DigestView({ digest }: { digest: Digest | null }) {
  if (!digest) {
    return (
      <SurfaceCard className="onboardingEmpty">
        <div className="emptyIcon">
          <FileSearch size={24} />
        </div>
        <h2>今天还没有可展示的简报</h2>
        <p>
          如果是首次使用，先确认来源和 LLM 已配置，然后执行“一键生成今日简报”。已有入库内容时，也可以先去信息库检索和复核。
        </p>
        <div className="onboardingActions">
          <Link className="linkButton compactLink" href="/admin/jobs">
            去生成简报
          </Link>
          <Link className="ghostLink compactLink" href="/admin/sources">
            检查来源
          </Link>
          <Link className="ghostLink compactLink" href="/library">
            打开信息库
          </Link>
        </div>
      </SurfaceCard>
    );
  }

  return (
    <div className="pageStack digestStack">
      <PageHeader
        eyebrow={`Version ${digest.version}`}
        title={digest.title}
        description={digest.overview_zh || "本期暂无概览。"}
        aside={
          <div className="metricStrip compactStats">
            <MetricCard label="专题" value={digest.stats.topic_count ?? 0} />
            <MetricCard label="条目" value={digest.stats.item_count ?? 0} />
            <MetricCard label="来源" value={digest.stats.source_count ?? 0} />
          </div>
        }
      />

      <section className="digestList">
        <div className="sectionTitleRow">
          <div>
            <h2>精选条目</h2>
            <p className="mutedText">按全局重要性和来源均衡策略排序展示。</p>
          </div>
          <span className="statusBadge success">
            <Sparkles size={13} />
            中文摘要
          </span>
        </div>

        {digest.items.map((item) => {
          const sourceUrl = originalUrl(item.source_snapshot);

          return (
            <article key={item.id} className="digestItem digestCard">
              <div className="rankPill">
                <TrendingUp size={15} />
                {item.rank}
              </div>
              <div className="digestBody">
                <div className="digestMeta">
                  <span>{sourceLabel(item.source_snapshot) || categoryLabels[item.category_snapshot] || item.category_snapshot}</span>
                  <span>分数 {item.score_snapshot.toFixed(2)}</span>
                  <span>来源 {String(item.source_snapshot.source_count ?? 0)}</span>
                </div>
                <h2>{item.title_snapshot}</h2>
                <p>{item.summary_snapshot_zh || "该专题尚未生成中文摘要。"}</p>
                <p className="mutedText">
                  {item.importance_snapshot_zh || "重要性说明将在摘要任务完成后补齐。"}
                </p>
                {sourceUrl ? (
                  <a className="linkButton compactLink" href={sourceUrl} target="_blank" rel="noreferrer">
                    查看原文
                    <ExternalLink size={14} />
                  </a>
                ) : null}
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}

function sourceLabel(sourceSnapshot: Record<string, unknown>) {
  const sourceName = stringValue(
    sourceSnapshot.primary_source_name ?? sourceSnapshot.source_name
  );
  if (sourceName) return sourceName;

  const sourceType = stringValue(
    sourceSnapshot.primary_source_type ?? sourceSnapshot.source_type
  );
  if (!sourceType) return null;
  return sourceTypeLabels[sourceType] || sourceType;
}

function originalUrl(sourceSnapshot: Record<string, unknown>) {
  return stringValue(
    sourceSnapshot.primary_url ?? sourceSnapshot.url ?? sourceSnapshot.canonical_url
  );
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
