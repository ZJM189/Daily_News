"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { LibraryAnalyticsPanel } from "../components/LibraryAnalyticsPanel";
import { PaginationBar } from "../components/PaginationBar";
import { CardHeader, Notice, PageHeader, PageScaffold, SurfaceCard } from "../components/UiPrimitives";
import { createSavedSearch, getLibraryAnalytics, searchLibraryItems } from "../../lib/api";
import type {
  LibraryAnalytics,
  LibraryAnalyticsDimension,
  LibraryAnalyticsScoreBucket,
  LibraryItem,
  PageMeta
} from "../../lib/types";

type SelectOption = {
  value: string;
  label: string;
};

type LibraryFilters = {
  keyword: string;
  category: string;
  sourceType: string;
  sort: string;
  minScore: string;
  hasSummary: string;
};

const emptyFilters: LibraryFilters = {
  keyword: "",
  category: "",
  sourceType: "",
  sort: "latest",
  minScore: "",
  hasSummary: ""
};

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
  const [keyword, setKeyword] = useState(emptyFilters.keyword);
  const [category, setCategory] = useState(emptyFilters.category);
  const [sourceType, setSourceType] = useState(emptyFilters.sourceType);
  const [sort, setSort] = useState(emptyFilters.sort);
  const [minScore, setMinScore] = useState(emptyFilters.minScore);
  const [hasSummary, setHasSummary] = useState(emptyFilters.hasSummary);
  const [pageSize, setPageSize] = useState(20);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<LibraryItem[]>([]);
  const [analytics, setAnalytics] = useState<LibraryAnalytics | null>(null);
  const [meta, setMeta] = useState<PageMeta>({ page: 1, page_size: 20, total: 0 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [analyticsCollapsed, setAnalyticsCollapsed] = useState(true);
  const [analyticsWindow, setAnalyticsWindow] = useState("30");
  const [savingSearch, setSavingSearch] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const selectedItem = useMemo(
    () => items.find((item) => item.id === selectedId) ?? items[0] ?? null,
    [items, selectedId]
  );
  const categoryFilterOptions = useMemo(
    () => mergeDimensionOptions(categoryOptions, analytics?.categories),
    [analytics?.categories]
  );
  const sourceTypeFilterOptions = useMemo(
    () => mergeDimensionOptions(sourceTypeOptions, analytics?.source_types),
    [analytics?.source_types]
  );

  function currentFilters(): LibraryFilters {
    return {
      keyword,
      category,
      sourceType,
      sort,
      minScore,
      hasSummary
    };
  }

  function applyFilters(filters: LibraryFilters) {
    setKeyword(filters.keyword);
    setCategory(filters.category);
    setSourceType(filters.sourceType);
    setSort(filters.sort);
    setMinScore(filters.minScore);
    setHasSummary(filters.hasSummary);
    setPage(1);
  }

  function buildParams(nextPage = page, filters = currentFilters(), nextPageSize = pageSize) {
    const params = buildFilterParams(filters);
    params.set("page", String(nextPage));
    params.set("page_size", String(nextPageSize));
    params.set("sort", filters.sort);
    return params;
  }

  function buildAnalyticsParams(filters = currentFilters(), windowDays = analyticsWindow) {
    const params = buildFilterParams(filters);
    params.set("window_days", windowDays);
    return params;
  }

  async function loadItems(nextPage = page, filters = currentFilters(), nextPageSize = pageSize) {
    setLoading(true);
    setError(null);
    try {
      const result = await searchLibraryItems(buildParams(nextPage, filters, nextPageSize));
      setItems(result.data);
      setMeta(result.meta);
      setPage(result.meta.page);
      setPageSize(result.meta.page_size);
      setSelectedId(result.data[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "信息库加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadAnalytics(filters = currentFilters(), windowDays = analyticsWindow) {
    setAnalyticsLoading(true);
    setError(null);
    try {
      setAnalytics(await getLibraryAnalytics(buildAnalyticsParams(filters, windowDays)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "信息库统计加载失败");
    } finally {
      setAnalyticsLoading(false);
    }
  }

  async function reloadLibrary(nextPage = 1, filters = currentFilters()) {
    await Promise.all([loadItems(nextPage, filters), loadAnalytics(filters)]);
  }

  async function handlePageSizeChange(nextPageSize: number) {
    setPageSize(nextPageSize);
    await loadItems(1, currentFilters(), nextPageSize);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void reloadLibrary(1, currentFilters());
  }

  function resetFilters() {
    applyFilters(emptyFilters);
    void reloadLibrary(1, emptyFilters);
  }

  function applyAnalyticsFilter(patch: Partial<LibraryFilters>) {
    const nextFilters = { ...currentFilters(), ...patch };
    applyFilters(nextFilters);
    void reloadLibrary(1, nextFilters);
  }

  function handleAnalyticsWindowChange(value: string) {
    setAnalyticsWindow(value);
    void loadAnalytics(currentFilters(), value);
  }

  async function saveCurrentSearch() {
    const filters = currentFilters();
    const query: Record<string, unknown> = {};
    if (filters.keyword.trim()) query.keyword = filters.keyword.trim();
    if (filters.category) query.category = filters.category;
    if (filters.sourceType) query.source_type = filters.sourceType;
    if (filters.minScore) query.min_score = Number(filters.minScore);
    if (filters.hasSummary) query.has_summary = filters.hasSummary === "true";
    query.sort = filters.sort;

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
    void reloadLibrary(1, emptyFilters);
  }, []);

  const totalPages = Math.max(1, Math.ceil(meta.total / meta.page_size));

  return (
    <PageScaffold>
      <PageHeader
        eyebrow="内容检索"
        title="信息库"
        description="检索全量入库内容，按来源、分类、摘要状态和分数快速复核，也可以保存当前搜索条件用于我的关注。"
        actions={
          <div className="actionBar">
          <button className="ghostButton" type="button" onClick={() => void saveCurrentSearch()}>
            {savingSearch ? "保存中" : "保存当前搜索"}
          </button>
          <button
            className="ghostButton"
            type="button"
            onClick={() => void reloadLibrary(page, currentFilters())}
          >
            刷新
          </button>
        </div>
        }
      />

      <SurfaceCard className="filterCard">
        <CardHeader
          title="筛选检索"
          description="筛选条件会同时驱动列表和数据洞察，保存后可作为我的关注规则。"
        />
        <form className="filterPanel" onSubmit={handleSubmit}>
          <input
            className="searchInput"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索标题、摘要、标签"
          />
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {categoryFilterOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <select value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
            {sourceTypeFilterOptions.map((option) => (
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
      </SurfaceCard>

      {error ? <Notice tone="danger" compact>{error}</Notice> : null}
      {message ? <Notice tone="success">{message}</Notice> : null}

      <LibraryAnalyticsPanel
        analytics={analytics}
        loading={analyticsLoading}
        collapsed={analyticsCollapsed}
        windowDays={analyticsWindow}
        onWindowChange={handleAnalyticsWindowChange}
        onToggleCollapsed={() => setAnalyticsCollapsed((collapsed) => !collapsed)}
        onSourceTypeSelect={(value) => applyAnalyticsFilter({ sourceType: value })}
        onCategorySelect={(value) => applyAnalyticsFilter({ category: value })}
        onScoreBucketSelect={(bucket) =>
          applyAnalyticsFilter({
            minScore: bucket.min_score === null ? "" : String(Math.trunc(bucket.min_score))
          })
        }
      />

      <section className="libraryLayout">
        <div className="libraryList">
          <div className="sectionTitleRow listSummary">
            <div>
              <h2>检索结果</h2>
              <p className="mutedText">共 {meta.total} 条，当前第 {meta.page}/{totalPages} 页</p>
            </div>
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
          <PaginationBar
            meta={meta}
            loading={loading}
            onPageChange={(nextPage) => loadItems(nextPage)}
            onPageSizeChange={handlePageSizeChange}
          />
        </div>

        <aside className="detailPanel detailCard">
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
    </PageScaffold>
  );
}

function buildFilterParams(filters: LibraryFilters) {
  const params = new URLSearchParams();
  if (filters.keyword.trim()) params.set("keyword", filters.keyword.trim());
  if (filters.category) params.set("category", filters.category);
  if (filters.sourceType) params.set("source_type", filters.sourceType);
  if (filters.minScore) params.set("min_score", filters.minScore);
  if (filters.hasSummary) params.set("has_summary", filters.hasSummary);
  return params;
}

function mergeDimensionOptions(
  baseOptions: SelectOption[],
  dimensions: LibraryAnalyticsDimension[] | undefined
) {
  const optionMap = new Map(baseOptions.map((option) => [option.value, option]));
  for (const dimension of dimensions ?? []) {
    if (!optionMap.has(dimension.key)) {
      optionMap.set(dimension.key, {
        value: dimension.key,
        label: dimension.label
      });
    }
  }
  return Array.from(optionMap.values());
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
