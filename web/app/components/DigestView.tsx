import Link from "next/link";
import {
  Clock3,
  ExternalLink,
  FileSearch,
  Sparkles,
  TrendingUp
} from "lucide-react";
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
  hugging_face: "Hugging Face",
};

type DigestViewProps = {
  digest: Digest | null;
  mode?: "workspace" | "public";
};

export function DigestView({ digest, mode = "workspace" }: DigestViewProps) {
  if (mode === "public") {
    return <PublicDigestView digest={digest} />;
  }

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

function PublicDigestView({ digest }: { digest: Digest | null }) {
  if (!digest) {
    return (
      <div className="publicDigestStack">
        <section className="publicDigestEmpty">
          <p className="publicIssueDate">{formatDigestDate(todayInShanghai())}</p>
          <h1>今日 AI 简报正在整理</h1>
          <p>采集和摘要完成后，本页会自动发布今日的 AI 行业要闻。</p>
          <div className="publicEmptyActions">
            <Link href="/today">刷新页面</Link>
            <Link href="/login?next=%2Ftoday">登录工作区</Link>
          </div>
        </section>
      </div>
    );
  }

  const generatedLabel = formatTimestamp(digest.published_at || digest.generated_at || digest.created_at);
  const topicCount = digest.stats.topic_count ?? digest.items.length;
  const itemCount = digest.stats.item_count ?? digest.items.length;
  const sourceCount = digest.stats.source_count ?? 0;

  return (
    <div className="publicDigestStack">
      <section className="publicDigestMasthead" aria-labelledby="public-digest-title">
        <p className="publicIssueDate">{formatDigestDate(digest.digest_date)}</p>
        <h1 id="public-digest-title">{digest.title}</h1>
        <p className="publicDigestOverview">{digest.overview_zh || "本期暂无概览。"}</p>
        <div className="publicDigestFacts" aria-label="本期简报概况">
          <span><strong>{topicCount}</strong> 个专题</span>
          <span><strong>{itemCount}</strong> 条内容</span>
          <span><strong>{sourceCount}</strong> 个来源</span>
          <span className="publicUpdatedAt">
            <Clock3 size={14} aria-hidden="true" />
            {generatedLabel ? `${generatedLabel} 更新` : "发布时间待定"}
          </span>
        </div>
      </section>

      <section className="publicPortalLayout" id="public-digest-list">
        <div className="publicNewsStream" aria-label="今日要闻">
          <header className="publicStreamHeader">
            <h2>今日要闻</h2>
            <span>{digest.items.length} 条精选</span>
          </header>

          <div className="publicDigestList">
            {digest.items.map((item, index) => {
              const sourceUrl = originalUrl(item.source_snapshot);
              const category = categoryLabels[item.category_snapshot] || item.category_snapshot;
              const source = sourceLabel(item.source_snapshot) || category;
              const itemSourceCount = numberValue(item.source_snapshot.source_count);
              const itemId = `public-digest-item-${item.rank}`;

              return (
                <article
                  className={`publicDigestItem ${index === 0 ? "publicDigestLead" : ""}`}
                  id={itemId}
                  key={item.id}
                >
                  <div className="publicItemMeta">
                    <span className="publicItemRank">{String(item.rank).padStart(2, "0")}</span>
                    <span className="publicItemSource">{source}</span>
                    <span aria-hidden="true">/</span>
                    <span>{category}</span>
                    {itemSourceCount > 1 ? <span>{itemSourceCount} 个相关来源</span> : null}
                  </div>
                  <h2>
                    {sourceUrl ? (
                      <a href={sourceUrl} target="_blank" rel="noreferrer">
                        {item.title_snapshot}
                      </a>
                    ) : item.title_snapshot}
                  </h2>
                  <p className="publicItemSummary">
                    {item.summary_snapshot_zh || "该专题尚未生成中文摘要。"}
                  </p>
                  {item.importance_snapshot_zh ? (
                    <p className="publicItemImportance">
                      <strong>影响</strong>
                      {item.importance_snapshot_zh}
                    </p>
                  ) : null}
                  <footer className="publicItemFooter">
                    <span>{formatItemTimestamp(item.created_at)} 收录</span>
                    {sourceUrl ? (
                      <a href={sourceUrl} target="_blank" rel="noreferrer">
                        查看原文
                        <ExternalLink size={13} aria-hidden="true" />
                      </a>
                    ) : null}
                  </footer>
                </article>
              );
            })}
          </div>
        </div>

        <aside className="publicDigestIndex" aria-label="今日索引">
          <header>
            <h2>今日索引</h2>
            <span>第 {digest.version} 版</span>
          </header>
          <ol>
            {digest.items.map((item) => (
              <li key={item.id}>
                <a href={`#public-digest-item-${item.rank}`}>
                  <span>{String(item.rank).padStart(2, "0")}</span>
                  <span>
                    <strong>{item.title_snapshot}</strong>
                    <small>{categoryLabels[item.category_snapshot] || item.category_snapshot}</small>
                  </span>
                </a>
              </li>
            ))}
          </ol>
          <p>{itemCount} 条内容，来自 {sourceCount} 个信息源</p>
        </aside>
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

function numberValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDigestDate(value: string) {
  const date = new Date(`${value}T00:00:00+08:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short"
  }).format(date);
}

function formatTimestamp(value: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatItemTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "本期";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function todayInShanghai() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).format(new Date());
}
