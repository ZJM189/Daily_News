"use client";

import { FormEvent, useEffect, useState } from "react";
import { PaginationBar } from "../components/PaginationBar";
import { createFeedback, getUserPreference, listFollowingItems, saveUserPreference } from "../../lib/api";
import type { FollowingItem, PageMeta, UserPreference } from "../../lib/types";

const emptyPreference: UserPreference = {
  follow_keywords: [],
  exclude_keywords: [],
  follow_categories: [],
  follow_source_types: [],
  disabled_source_types: [],
  blocked_source_ids: [],
  blocked_domains: [],
  weights: {}
};

const categoryOptions = [
  { value: "model_company", label: "模型公司" },
  { value: "open_source", label: "开源项目" },
  { value: "research_paper", label: "研究论文" },
  { value: "product_launch", label: "产品发布" },
  { value: "community", label: "社区动态" },
  { value: "industry_funding", label: "产业融资" },
  { value: "other", label: "其他" }
];

const sourceTypeOptions = [
  { value: "rss", label: "RSS" },
  { value: "github", label: "GitHub" },
  { value: "arxiv", label: "arXiv" },
  { value: "hacker_news", label: "Hacker News" },
  { value: "product_hunt", label: "Product Hunt" },
  { value: "hugging_face", label: "Hugging Face" }
];

export default function FollowingPage() {
  const [preference, setPreference] = useState<UserPreference>(emptyPreference);
  const [keywordInput, setKeywordInput] = useState("");
  const [excludeInput, setExcludeInput] = useState("");
  const [domainInput, setDomainInput] = useState("");
  const [feed, setFeed] = useState<FollowingItem[]>([]);
  const [meta, setMeta] = useState<PageMeta>({ page: 1, page_size: 20, total: 0 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const preferenceFormId = "following-preference-form";

  async function load(page = 1) {
    setLoading(true);
    setError(null);
    try {
      const [nextPreference, nextFeed] = await Promise.all([getUserPreference(), listFollowingItems(page)]);
      setPreference(nextPreference);
      setFeed(nextFeed.data);
      setMeta(nextFeed.meta);
    } catch (err) {
      setError(err instanceof Error ? err.message : "关注内容加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await saveUserPreference(preference);
      setMessage("关注已保存");
      await load(meta.page);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  }

  async function handleFeedback(entry: FollowingItem, action: "more_like" | "less_like" | "block_source") {
    setMessage(null);
    setError(null);
    try {
      await createFeedback({
        action,
        item_id: action === "block_source" ? undefined : entry.item.id,
        source_id: action === "block_source" ? entry.item.source.id : undefined
      });
      setMessage(action === "block_source" ? "已屏蔽该来源" : "反馈已记录");
      if (action === "block_source") {
        await load(meta.page);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "反馈失败，请稍后重试");
    }
  }

  function addToken(field: "follow_keywords" | "exclude_keywords" | "blocked_domains", value: string) {
    const cleaned = value.trim();
    if (!cleaned || preference[field].some((item) => item.toLowerCase() === cleaned.toLowerCase())) {
      return;
    }
    setPreference({ ...preference, [field]: [...preference[field], cleaned] });
  }

  function removeToken(field: "follow_keywords" | "exclude_keywords" | "blocked_domains", value: string) {
    setPreference({
      ...preference,
      [field]: preference[field].filter((item) => item !== value)
    });
  }

  function toggleList(field: "follow_categories" | "follow_source_types" | "disabled_source_types", value: string) {
    const current = preference[field];
    setPreference({
      ...preference,
      [field]: current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value]
    });
  }

  useEffect(() => {
    void load();
  }, []);

  const hasRules = Boolean(
    preference.follow_keywords.length ||
      preference.exclude_keywords.length ||
      preference.follow_categories.length ||
      preference.follow_source_types.length ||
      preference.disabled_source_types.length ||
      preference.blocked_source_ids.length ||
      preference.blocked_domains.length
  );
  const totalPages = Math.max(1, Math.ceil(meta.total / meta.page_size));

  return (
    <main className="pageSurface">
      <section className="pageHeader">
        <div>
          <p className="eyebrow">个性化信息流</p>
          <h1>我的关注</h1>
          <p className="description">左侧保存当前关注偏好，右侧展示当前生效规则。</p>
        </div>
        <button className="ghostButton" type="button" onClick={() => void load(meta.page)}>
          刷新
        </button>
      </section>

      {message ? <section className="infoState">{message}</section> : null}
      {error ? <section className="errorState compact">{error}</section> : null}

      <section className="followingLayout">
        <form className="preferencePanel" id={preferenceFormId} onSubmit={handleSave}>
          <h2>当前关注规则</h2>
          <p className="mutedText">
            关键词、分类和来源类型用于软加权，排除词、屏蔽来源和禁用来源类型会直接过滤。
          </p>
          <TagEditor
            label="关注关键词"
            placeholder="例如：OpenAI、Agent、AI 编程"
            value={keywordInput}
            tokens={preference.follow_keywords}
            onChange={setKeywordInput}
            onAdd={() => {
              addToken("follow_keywords", keywordInput);
              setKeywordInput("");
            }}
            onRemove={(token) => removeToken("follow_keywords", token)}
          />
          <TagEditor
            label="排除关键词"
            placeholder="例如：招聘、广告、无关厂商"
            value={excludeInput}
            tokens={preference.exclude_keywords}
            onChange={setExcludeInput}
            onAdd={() => {
              addToken("exclude_keywords", excludeInput);
              setExcludeInput("");
            }}
            onRemove={(token) => removeToken("exclude_keywords", token)}
          />
          <fieldset>
            <legend>关注分类</legend>
            <div className="checkGrid">
              {categoryOptions.map((option) => (
                <label key={option.value}>
                  <input
                    type="checkbox"
                    checked={preference.follow_categories.includes(option.value)}
                    onChange={() => toggleList("follow_categories", option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>关注来源类型</legend>
            <div className="checkGrid">
              {sourceTypeOptions.map((option) => (
                <label key={option.value}>
                  <input
                    type="checkbox"
                    checked={preference.follow_source_types.includes(option.value)}
                    onChange={() => toggleList("follow_source_types", option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>禁用来源类型</legend>
            <div className="checkGrid">
              {sourceTypeOptions.map((option) => (
                <label key={option.value}>
                  <input
                    type="checkbox"
                    checked={preference.disabled_source_types.includes(option.value)}
                    onChange={() => toggleList("disabled_source_types", option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
          <TagEditor
            label="屏蔽域名"
            placeholder="例如：example.com"
            value={domainInput}
            tokens={preference.blocked_domains}
            onChange={setDomainInput}
            onAdd={() => {
              addToken("blocked_domains", domainInput);
              setDomainInput("");
            }}
            onRemove={(token) => removeToken("blocked_domains", token)}
          />
          <button type="submit" disabled={saving}>
            {saving ? "保存中" : "保存当前关注"}
          </button>
        </form>

        <div className="followingFeed">
          <section className="rulePanel">
            <div className="sectionHead">
              <div>
                <h2>当前生效规则</h2>
                <p className="mutedText">保存后会立刻影响右侧关注流预览。</p>
              </div>
              <button
                className="ghostButton"
                type="button"
                onClick={() => {
                  document.getElementById(preferenceFormId)?.scrollIntoView({ behavior: "smooth", block: "start" });
                }}
              >
                编辑
              </button>
            </div>
            {!hasRules ? (
              <div className="emptyState compact">当前没有生效规则。</div>
            ) : (
              <div className="ruleSummaryGrid">
                <RuleGroup label="关注关键词" tokens={preference.follow_keywords} />
                <RuleGroup label="排除关键词" tokens={preference.exclude_keywords} />
                <RuleGroup label="关注分类" tokens={preference.follow_categories.map(categoryLabel)} />
                <RuleGroup
                  label="关注来源类型"
                  tokens={preference.follow_source_types.map(sourceTypeLabel)}
                />
                <RuleGroup
                  label="禁用来源类型"
                  tokens={preference.disabled_source_types.map(sourceTypeLabel)}
                />
                <RuleGroup label="屏蔽域名" tokens={preference.blocked_domains} />
                <RuleGroup
                  label="屏蔽来源"
                  tokens={preference.blocked_source_ids.map((value) => shortId(value))}
                />
              </div>
            )}
          </section>

          <div className="listSummary">
            <strong>关注流 {meta.total}</strong>
            <span>
              第 {meta.page}/{totalPages} 页
            </span>
          </div>
          {loading ? <div className="emptyState">正在根据规则生成预览</div> : null}
          {!loading && !hasRules ? (
            <div className="emptyState">还没有关注规则，添加关键词后生成你的信息流。</div>
          ) : null}
          {!loading && hasRules && feed.length === 0 ? (
            <div className="emptyState">当前规则下暂无内容，可以放宽关键词或来源限制。</div>
          ) : null}
          {!loading
            ? feed.map((entry) => (
                <article key={entry.item.id} className="followingItem">
                  <div className="digestMeta">
                    <span>个性分 {entry.personalized_score.toFixed(1)}</span>
                    <span>{categoryLabel(entry.item.category)}</span>
                    <span>{entry.item.source.name}</span>
                  </div>
                  <h2>{entry.item.title}</h2>
                  <p>{entry.item.summary_zh || entry.item.content_snippet || "该条目暂无摘要。"}</p>
                  <div className="reasonList">
                    {entry.match_reasons.map((reason) => (
                      <span key={reason}>{reason}</span>
                    ))}
                  </div>
                  <div className="itemActions">
                    <button className="ghostButton" type="button" onClick={() => void handleFeedback(entry, "more_like")}>
                      多看类似
                    </button>
                    <button className="ghostButton" type="button" onClick={() => void handleFeedback(entry, "less_like")}>
                      少看类似
                    </button>
                    <button className="ghostButton" type="button" onClick={() => void handleFeedback(entry, "block_source")}>
                      屏蔽来源
                    </button>
                    <a href={entry.item.url} target="_blank" rel="noreferrer">
                      查看原文
                    </a>
                  </div>
                </article>
              ))
            : null}
          <PaginationBar meta={meta} loading={loading} onPageChange={load} />
        </div>
      </section>
    </main>
  );
}

function TagEditor({
  label,
  placeholder,
  value,
  tokens,
  onChange,
  onAdd,
  onRemove
}: {
  label: string;
  placeholder: string;
  value: string;
  tokens: string[];
  onChange: (value: string) => void;
  onAdd: () => void;
  onRemove: (token: string) => void;
}) {
  return (
    <label className="tagEditor">
      <span>{label}</span>
      <div className="inlineForm">
        <input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
        <button className="ghostButton" type="button" onClick={onAdd}>
          添加
        </button>
      </div>
      <div className="tagList">
        {tokens.map((token) => (
          <button key={token} className="tagRemove" type="button" onClick={() => onRemove(token)}>
            {token} ×
          </button>
        ))}
      </div>
    </label>
  );
}

function RuleGroup({ label, tokens }: { label: string; tokens: string[] }) {
  return (
    <section className="ruleGroup">
      <strong>{label}</strong>
      {tokens.length ? (
        <div className="ruleChipList">
          {tokens.map((token) => (
            <span key={token} className="ruleChip">
              {token}
            </span>
          ))}
        </div>
      ) : (
        <span className="mutedText">未设置</span>
      )}
    </section>
  );
}

function categoryLabel(value: string) {
  return categoryOptions.find((item) => item.value === value)?.label || value;
}

function sourceTypeLabel(value: string) {
  return sourceTypeOptions.find((item) => item.value === value)?.label || value;
}

function shortId(value: string) {
  if (value.length <= 10) {
    return value;
  }
  return `${value.slice(0, 6)}…${value.slice(-4)}`;
}
