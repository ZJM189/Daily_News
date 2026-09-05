"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { PaginationBar } from "../components/PaginationBar";
import { createSavedSearch, searchLibraryItems } from "../../lib/api";
import type { LibraryItem, PageMeta } from "../../lib/types";

const categoryOptions = [
  { value: "", label: "全部分类" },
  { value: "model_company", label: "模型公司" },
  { value: "open_source", label: "开源项目" },
  { value: "research_paper", label: "研究论文" },
  { value: "product_launch", label: "产品发布" },
  { value: "community", label: "社区动态" },
  { value: "industry_funding", label: "产业融资" },
  { value: "other", label: "其他" }
];

const sourceTypeOptions = [
  { value: "", label: "全部来源类型" },
  { value: "rss", label: "RSS" },
  { value: "github", label: "GitHub" },
  { value: "arxiv", label: "arXiv" },
  { value: "hacker_news", label: "Hacker News" },
  { value: "product_hunt", label: "Product Hunt" },
  { value: "hugging_face", label: "Hugging Face" }
];

const sortOptions = [
  { value: "latest", label: "最新优先" },
  { value: "score", label: "重要性优先" },
  { value: "collected", label: "入库时间优先" }
];

export default function LibraryPage() {
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [sort, setSort] = useState("latest");
  const [minScore, setMinScore] = useState("");
  const [hasSummary, setHasSummary] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [meta, setMeta] = useState<PageMeta>({ page: 1, page_size: 20, total: 0 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingSearch, setSavingSearch] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedId) ?? items[0] ?? null,
    [items, selectedId]
  );

  function buildParams(nextPage = page) {
    const params = new URLSearchParams();
    params.set("page", String(nextPage));
    params.set("page_size", "20");
    params.set("sort", sort);
    if (keyword.trim()) params.set("keyword", keyword.trim());
    if (category) params.set("category", category);
    if (sourceType) params.set("source_type", sourceType);
    if (minScore) params.set("min_score", minScore);
    if (hasSummary) params.set("has_summary", hasSummary);
    return params;
  }

  async function loadItems(nextPage = page) {
    setLoading(true);
    setError(null);
    try {
      const result = await searchLibraryItems(buildParams(nextPage));
      setItems(result.data);
      setMeta(result.meta);
      setPage(result.meta.page);
      setSelectedId(result.data[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "信息库加载失败");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadItems(1);
  }

  function resetFilters() {
    setKeyword("");
    setCategory("");
    setSourceType("");
    setSort("latest");
    setMinScore("");
    setHasSummary("");
    setPage(1);
  }

  async function saveCurrentSearch() {
    const query: Record<string, unknown> = {};
    if (keyword.trim()) query.keyword = keyword.trim();
    if (category) query.category = category;
    if (sourceType) query.source_type = sourceType;
    if (minScore) query.min_score = Number(minScore);
    if (hasSummary) query.has_summary = hasSummary === "true";
    query.sort = sort;

    setSavingSearch(true);
    setError(null);
    setMessage(null);
    try {
      await createSavedSearch({
        name: buildSearchName(query),
        query,
        apply_as_filter: true,
        apply_as_boost: true
      });
      setMessage("当前搜索条件已保存到我的关注，会参与关注流排序和过滤");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存搜索失败");
    } finally {
      setSavingSearch(false);
    }
  }

  useEffect(() => {
    void loadItems(1);
  }, []);

  const totalPages = Math.max(1, Math.ceil(meta.total / meta.page_size));

  return (
    <main className="pageSurface">
      <section className="pageHeader">
        <div>
          <p className="eyebrow">内容检索</p>
          <h1>信息库</h1>
          <p className="description">检索全量入库内容，按来源、分类、摘要状态和分数快速复核，也可以保存当前搜索条件用于我的关注。</p>
        </div>
        <div className="actionBar">
          <button className="ghostButton" type="button" onClick={() => void saveCurrentSearch()}>
            {savingSearch ? "保存中" : "保存当前搜索"}
          </button>
          <button className="ghostButton" type="button" onClick={() => void loadItems(page)}>
            刷新
          </button>
        </div>
      </section>

      <form className="filterPanel" onSubmit={handleSubmit}>
        <input
          className="searchInput"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="搜索标题、摘要、标签"
        />
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          {categoryOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
          {sourceTypeOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select value={sort} onChange={(event) => setSort(event.target.value)}>
          {sortOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <input
          type="number"
          min="0"
          max="100"
          value={minScore}
          onChange={(event) => setMinScore(event.target.value)}
          placeholder="最低分"
        />
        <select value={hasSummary} onChange={(event) => setHasSummary(event.target.value)}>
          <option value="">摘要状态</option>
          <option value="true">已摘要</option>
          <option value="false">待摘要</option>
        </select>
        <button type="submit" disabled={loading}>
          {loading ? "检索中" : "检索"}
        </button>
        <button className="ghostButton" type="button" onClick={resetFilters}>
          重置
        </button>
      </form>

      {error ? <section className="errorState compact">{error}</section> : null}
      {message ? <section className="infoState">{message}</section> : null}

      <section className="libraryLayout">
        <div className="libraryList">
          <div className="listSummary">
            <strong>结果 {meta.total}</strong>
            <span>
              第 {meta.page}/{totalPages} 页
            </span>
          </div>
          {loading ? <div className="emptyState">正在加载信息库内容</div> : null}
          {!loading && items.length === 0 ? (
            <div className="emptyState">没有找到匹配内容，试试放宽筛选条件。</div>
          ) : null}
          {!loading
            ? items.map((item) => (
                <button
                  key={item.id}
                  className={`libraryRow ${selectedItem?.id === item.id ? "active" : ""}`}
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                >
                  <span className="libraryRowTitle">{item.title}</span>
                  <span className="libraryRowSummary">
                    {item.summary_zh || item.content_snippet || "该条目暂无摘要。"}
                  </span>
                  <span className="libraryRowMeta">
                    <span>{categoryLabel(item.category)}</span>
                    <span>{item.source.name}</span>
                    <span>分数 {item.score.toFixed(1)}</span>
                    <span>{formatDate(item.published_at || item.collected_at)}</span>
                  </span>
                </button>
              ))
            : null}
          <PaginationBar meta={meta} loading={loading} onPageChange={loadItems} />
        </div>

        <aside className="detailPanel">
          {selectedItem ? (
            <>
              <div className="detailHeader">
                <span className="statusBadge">{selectedItem.status}</span>
                <span className="statusBadge">{selectedItem.summary_zh ? "已摘要" : "待摘要"}</span>
              </div>
              <h2>{selectedItem.title}</h2>
              <p>{selectedItem.summary_zh || selectedItem.content_snippet || "暂无可展示摘要。"}</p>
              <p className="mutedText">
                {selectedItem.importance_zh || "重要性说明将在摘要任务完成后补齐。"}
              </p>
              <dl className="detailGrid">
                <div>
                  <dt>来源</dt>
                  <dd>{selectedItem.source.name}</dd>
                </div>
                <div>
                  <dt>分类</dt>
                  <dd>{categoryLabel(selectedItem.category)}</dd>
                </div>
                <div>
                  <dt>分数</dt>
                  <dd>{selectedItem.score.toFixed(1)}</dd>
                </div>
                <div>
                  <dt>发布时间</dt>
                  <dd>{formatDateTime(selectedItem.published_at || selectedItem.collected_at)}</dd>
                </div>
              </dl>
              <div className="tagList">
                {selectedItem.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
              <a className="linkButton" href={selectedItem.url} target="_blank" rel="noreferrer">
                查看原文
              </a>
            </>
          ) : (
            <div className="emptyState">选择一条内容查看详情。</div>
          )}
        </aside>
      </section>
    </main>
  );
}

function categoryLabel(value: string) {
  return categoryOptions.find((item) => item.value === value)?.label || value;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit"
  }).format(new Date(value));
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function buildSearchName(query: Record<string, unknown>) {
  if (typeof query.keyword === "string" && query.keyword) {
    return `${query.keyword} 相关内容`;
  }
  if (typeof query.category === "string" && query.category) {
    return `${categoryLabel(query.category)} 分类关注`;
  }
  if (typeof query.source_type === "string" && query.source_type) {
    return `${query.source_type} 来源关注`;
  }
  return "信息库搜索关注";
}
