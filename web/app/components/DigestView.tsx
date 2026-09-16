"use client";

import Link from "next/link";
import {
  useLayoutEffect,
  useRef,
  type MouseEvent
} from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  CalendarDays,
  Clock3,
  ExternalLink,
  FileSearch,
  Sparkles,
  TrendingUp
} from "lucide-react";
import type { Digest } from "../../lib/types";
import { MetricCard, PageHeader, SurfaceCard } from "./UiPrimitives";

const asciiNewsTitle = [
  "     ___    ____   _   __",
  "    /   |  /  _/  / | / /__ _      _______",
  "   / /| |  / /   /  |/ / _ \\ | /| / / ___/",
  "  / ___ |_/ /   / /|  /  __/ |/ |/ (__  )",
  " /_/  |_/___/  /_/ |_/\\___/|__/|__/____/"
].join("\n");

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
  selectedDate?: string;
  maxDate?: string;
  onDigestDateChange?: (date: string) => void;
};

export function DigestView({
  digest,
  mode = "workspace",
  selectedDate,
  maxDate,
  onDigestDateChange
}: DigestViewProps) {
  if (mode === "public") {
    return (
      <PublicDigestView
        digest={digest}
        selectedDate={selectedDate}
        maxDate={maxDate}
        onDigestDateChange={onDigestDateChange}
      />
    );
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
        title="AI News"
        titleNode={<AsciiNewsTitle compact />}
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

function PublicDigestView({
  digest,
  selectedDate,
  maxDate,
  onDigestDateChange
}: {
  digest: Digest | null;
  selectedDate?: string;
  maxDate?: string;
  onDigestDateChange?: (date: string) => void;
}) {
  const motionRoot = useRef<HTMLDivElement>(null);
  const activeDate = digest?.digest_date || selectedDate || todayInShanghai();
  const filteredItems = digest?.items ?? [];

  useLayoutEffect(() => {
    if (!motionRoot.current) return;
    gsap.registerPlugin(ScrollTrigger);

    const root = motionRoot.current;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const context = gsap.context(() => {
      const progress = root.querySelector<HTMLElement>(".publicReadingProgress");

      if (reducedMotion) {
        gsap.set(".publicReveal, .publicScrollReveal, .publicTickerTrack", {
          clearProps: "all"
        });
        if (progress) progress.style.transform = "scaleX(1)";
        return;
      }

      gsap.fromTo(
        ".publicReveal",
        { autoAlpha: 0, y: 28 },
        {
          autoAlpha: 1,
          y: 0,
          duration: 0.72,
          ease: "power3.out",
          stagger: 0.07,
          clearProps: "transform"
        }
      );

      gsap.utils.toArray<HTMLElement>(".publicScrollReveal").forEach((element) => {
        gsap.fromTo(
          element,
          { autoAlpha: 0, y: 22 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 0.62,
            ease: "power2.out",
            scrollTrigger: {
              trigger: element,
              start: "top 88%",
              once: true
            }
          }
        );
      });

      const tickerTrack = root.querySelector<HTMLElement>(".publicTickerTrack");
      const tickerViewport = tickerTrack?.parentElement;
      if (tickerTrack && tickerViewport && tickerTrack.scrollWidth > tickerViewport.clientWidth) {
        gsap.to(tickerTrack, {
          xPercent: -50,
          duration: Math.max(22, filteredItems.length * 5),
          ease: "none",
          repeat: -1
        });
      }

      if (progress) {
        ScrollTrigger.create({
          trigger: root,
          start: "top top",
          end: "bottom bottom",
          onUpdate: (self) => {
            progress.style.transform = `scaleX(${self.progress})`;
          }
        });
      }
    }, root);

    return () => context.revert();
  }, [activeDate, filteredItems.length]);

  if (!digest) {
    return (
      <div className="publicDigestStack" ref={motionRoot}>
        <section className="publicDigestEmpty">
          <PublicDigestDatePicker
            value={activeDate}
            maxDate={maxDate}
            onChange={onDigestDateChange}
          />
          <h1>{activeDate === todayInShanghai() ? "今日 AI 简报正在整理" : "所选日期暂无 AI 简报"}</h1>
          <p>采集和摘要完成后，本页会自动发布对应日期的 AI 行业要闻。</p>
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
  const leadItem = filteredItems[0] || null;
  const railItems = filteredItems.slice(1, 3);
  const remainingItems = filteredItems.slice(3);

  return (
    <div className="publicDigestStack" ref={motionRoot}>
      <div className="publicReadingProgress" aria-hidden="true" />

      <section className="publicDigestMasthead publicReveal" aria-labelledby="public-digest-title">
        <div className="publicMastheadTopline">
          <PublicDigestDatePicker
            value={digest.digest_date}
            maxDate={maxDate}
            onChange={onDigestDateChange}
          />
          <span className="publicLiveStatus">
            <span className="publicLiveDot" aria-hidden="true" />
            每日更新
          </span>
        </div>
        <div className="publicMastheadGrid">
          <div className="publicMastheadTitle">
            <h1 className="asciiNewsHeading" id="public-digest-title" aria-label="AI News">
              <AsciiNewsTitle />
            </h1>
          </div>
          <div className="publicMastheadCopy">
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
          </div>
        </div>
      </section>

      <section className="publicTicker publicReveal" aria-label="热点速览">
        <div className="publicTickerLabel">
          <TrendingUp size={15} aria-hidden="true" />
          热点速览
        </div>
        <div className="publicTickerViewport">
          <div className="publicTickerTrack">
            {[...filteredItems, ...filteredItems].map((item, index) => (
              <a
                className="publicTickerItem"
                href={`#public-digest-item-${item.rank}`}
                key={`${item.id}-${index}`}
              >
                <span>{String(item.rank).padStart(2, "0")}</span>
                {item.title_snapshot}
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="publicLeadGrid" aria-label="重点新闻">
        {leadItem ? <PublicLeadStory item={leadItem} /> : <PublicFilteredEmpty />}
        <div className="publicStoryRail">
          {railItems.map((item) => (
            <PublicRailStory item={item} key={item.id} />
          ))}
        </div>
      </section>

      <section className="publicPortalLayout" id="public-digest-list">
        {remainingItems.length > 0 ? (
          <div className="publicNewsStream" aria-label="今日要闻">
            <div className="publicDigestList">
              {remainingItems.map((item) => (
                <PublicDigestItem item={item} key={item.id} />
              ))}
            </div>
          </div>
        ) : null}
        <aside className="publicDigestIndex publicReveal" aria-label="今日索引">
          <header>
            <div>
              <span className="publicSectionKicker">READING INDEX</span>
              <h2>今日索引</h2>
            </div>
            <span>第 {digest.version} 版</span>
          </header>
          <ol>
            {filteredItems.map((item) => (
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
          <p>{filteredItems.length} 条内容，来自 {sourceCount} 个信息源</p>
        </aside>
      </section>
    </div>
  );
}

function PublicLeadStory({ item }: { item: Digest["items"][number] }) {
  const sourceUrl = originalUrl(item.source_snapshot);
  const category = categoryLabels[item.category_snapshot] || item.category_snapshot;
  const source = sourceLabel(item.source_snapshot) || category;

  return (
    <article className="publicLeadStory publicReveal" id={`public-digest-item-${item.rank}`}>
      <div className="publicLeadStoryBackdrop" aria-hidden="true">
        <span>{String(item.rank).padStart(2, "0")}</span>
      </div>
      <div className="publicLeadStoryContent">
        <div className="publicItemMeta">
          <span className="publicItemRank">{String(item.rank).padStart(2, "0")}</span>
          <span className="publicItemSource">{source}</span>
          <span aria-hidden="true">/</span>
          <span>{category}</span>
        </div>
        <h2>
          {sourceUrl ? (
            <a href={sourceUrl} target="_blank" rel="noreferrer">
              {item.title_snapshot}
            </a>
          ) : item.title_snapshot}
        </h2>
        <p>{item.summary_snapshot_zh || "该专题尚未生成中文摘要。"}</p>
        <div className="publicLeadStoryFooter">
          <span>重点报道 · {formatItemTimestamp(item.created_at)} 收录</span>
          {sourceUrl ? (
            <a href={sourceUrl} target="_blank" rel="noreferrer">
              阅读原文
              <ExternalLink size={13} aria-hidden="true" />
            </a>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function PublicRailStory({ item }: { item: Digest["items"][number] }) {
  const sourceUrl = originalUrl(item.source_snapshot);
  const category = categoryLabels[item.category_snapshot] || item.category_snapshot;

  return (
    <article className="publicRailStory publicReveal">
      <div className="publicRailRank">{String(item.rank).padStart(2, "0")}</div>
      <div>
        <span className="publicRailCategory">{category}</span>
        <h2>
          {sourceUrl ? (
            <a href={sourceUrl} target="_blank" rel="noreferrer">
              {item.title_snapshot}
            </a>
          ) : item.title_snapshot}
        </h2>
        <p>{sourceLabel(item.source_snapshot) || category}</p>
      </div>
    </article>
  );
}

function PublicFilteredEmpty() {
  return (
    <section className="publicFilteredEmpty">
      <TrendingUp size={20} aria-hidden="true" />
      <h2>这个专题暂时没有内容</h2>
      <p>切换其他专题，继续浏览本期 AI 简报。</p>
    </section>
  );
}

function PublicDigestItem({ item }: { item: Digest["items"][number] }) {
  const sourceUrl = originalUrl(item.source_snapshot);
  const category = categoryLabels[item.category_snapshot] || item.category_snapshot;
  const source = sourceLabel(item.source_snapshot) || category;
  const itemSourceCount = numberValue(item.source_snapshot.source_count);

  return (
    <article
      className="publicDigestItem publicScrollReveal"
      id={`public-digest-item-${item.rank}`}
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
}

function PublicDigestDatePicker({
  value,
  maxDate,
  onChange
}: {
  value: string;
  maxDate?: string;
  onChange?: (date: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const openDatePicker = (event: MouseEvent<HTMLLabelElement>) => {
    event.preventDefault();
    const input = inputRef.current;
    if (!input) return;

    input.focus();
    try {
      input.showPicker?.();
    } catch {
      input.click();
    }
  };

  return (
    <label className="publicDatePicker" onClick={openDatePicker}>
      <CalendarDays size={18} aria-hidden="true" />
      <span className="publicDatePickerLabel">{formatDigestDate(value)}</span>
      <input
        ref={inputRef}
        aria-label="选择简报日期"
        max={maxDate}
        type="date"
        value={value}
        onChange={(event) => {
          if (event.target.value) onChange?.(event.target.value);
        }}
      />
    </label>
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

function AsciiNewsTitle({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`asciiNewsTitle ${compact ? "compact" : ""}`} aria-hidden="true">
      {asciiNewsTitle}
    </span>
  );
}

function formatDigestDate(value: string) {
  const date = new Date(`${value}T00:00:00+08:00`);
  if (Number.isNaN(date.getTime())) return value;
  const monthDay = new Intl.DateTimeFormat("zh-CN", {
    month: "long",
    day: "numeric"
  }).format(date);
  const weekday = new Intl.DateTimeFormat("zh-CN", {
    weekday: "short"
  }).format(date);
  return `${monthDay} · ${weekday}`;
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
