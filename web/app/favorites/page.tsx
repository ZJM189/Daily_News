"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bookmark,
  ExternalLink,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  Trash2
} from "lucide-react";
import {
  FavoriteButton,
  useFavoriteItems,
  useFavorites
} from "../components/FavoritesProvider";
import { Modal } from "../components/Modal";
import { PaginationBar } from "../components/PaginationBar";
import { Notice, PageHeader, PageScaffold } from "../components/UiPrimitives";
import {
  createFavoriteFolder,
  deleteFavoriteFolder,
  renameFavoriteFolder,
  searchFavorites,
  favoriteCategoryLabels,
  favoriteSourceLabels,
  type FavoriteEntry,
  type FavoriteFolder
} from "../../lib/favorites";
import type { PageMeta } from "../../lib/types";

const emptyFilters = {
  keyword: "",
  category: "",
  source_type: "",
  sort: "saved"
};
type FolderAction =
  { mode: "create" } | { mode: "rename" | "delete"; folder: FavoriteFolder };

export default function FavoritesPage() {
  const { overview, revision, refresh, open, states, pending } = useFavorites();
  const [scope, setScope] = useState("all");
  const [draft, setDraft] = useState(emptyFilters);
  const [filters, setFilters] = useState(emptyFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [entries, setEntries] = useState<FavoriteEntry[]>([]);
  const [meta, setMeta] = useState<PageMeta>({
    page: 1,
    page_size: 20,
    total: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<FavoriteEntry | null>(null);
  const [folderAction, setFolderAction] = useState<FolderAction | null>(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const mutationLock = useRef(false);
  useFavoriteItems(entries.map((entry) => entry.item));

  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({
      ...filters,
      page: String(page),
      page_size: String(pageSize)
    });
    params.set("scope", scope === "all" || scope === "root" ? scope : "folder");
    if (scope !== "all" && scope !== "root") params.set("folder_id", scope);
    setLoading(true);
    setError(null);
    searchFavorites(params)
      .then((result) => {
        if (!active) return;
        const lastPage = Math.max(1, Math.ceil(result.meta.total / pageSize));
        if (page > lastPage) {
          setPage(lastPage);
          return;
        }
        setEntries(result.data);
        setMeta(result.meta);
      })
      .catch((err) => {
        if (active)
          setError(err instanceof Error ? err.message : "收藏加载失败");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [scope, filters, page, pageSize, revision]);

  useEffect(() => {
    if (
      overview &&
      scope !== "all" &&
      scope !== "root" &&
      !overview.folders.some((f) => f.id === scope)
    ) {
      setScope("root");
      setPage(1);
    }
  }, [overview, scope]);

  function chooseScope(value: string) {
    setScope(value);
    setPage(1);
  }
  function editFolder(action: FolderAction) {
    setFolderAction(action);
    setName(action.mode === "rename" ? action.folder.name : "");
    setActionError(null);
  }
  async function submitFolder() {
    if (!folderAction || mutationLock.current) return;
    mutationLock.current = true;
    setBusy(true);
    setActionError(null);
    try {
      if (folderAction.mode === "create")
        await createFavoriteFolder(name.trim());
      else if (folderAction.mode === "rename")
        await renameFavoriteFolder(folderAction.folder.id, name.trim());
      else {
        await deleteFavoriteFolder(folderAction.folder.id);
        if (scope === folderAction.folder.id) chooseScope("root");
      }
      setFolderAction(null);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "目录操作失败");
    } finally {
      mutationLock.current = false;
      setBusy(false);
    }
  }
  const folderName = (id: string | null) =>
    overview?.folders.find((f) => f.id === id)?.name ?? "根目录";
  const title =
    scope === "all"
      ? "全部收藏"
      : scope === "root"
        ? "根目录"
        : folderName(scope);
  const filtered = Boolean(
    filters.keyword || filters.category || filters.source_type
  );

  return (
    <PageScaffold>
      <PageHeader
        title="我的收藏"
        actions={
          <button
            className="favoriteIconButton"
            type="button"
            title="刷新收藏"
            aria-label="刷新收藏"
            disabled={loading}
            onClick={refresh}
          >
            <RefreshCw size={18} />
          </button>
        }
      />
      <section className="favoritesWorkspace">
        <aside className="favoritesFolders" aria-label="收藏目录">
          <div className="favoritesFolderHeading">
            <h2>目录</h2>
            <button
              className="favoriteIconButton"
              type="button"
              title="新建目录"
              aria-label="新建目录"
              onClick={() => editFolder({ mode: "create" })}
            >
              <FolderPlus size={18} />
            </button>
          </div>
          <label className="favoritesMobileFolder">
            当前目录
            <select value={scope} onChange={(e) => chooseScope(e.target.value)}>
              <option value="all">全部收藏 ({overview?.total ?? 0})</option>
              <option value="root">根目录 ({overview?.root_count ?? 0})</option>
              {overview?.folders.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({f.count})
                </option>
              ))}
            </select>
          </label>
          <nav className="favoritesFolderNav">
            <button
              className={scope === "all" ? "active" : ""}
              type="button"
              onClick={() => chooseScope("all")}
            >
              <Bookmark size={17} />
              <span>全部收藏</span>
              <small>{overview?.total ?? 0}</small>
            </button>
            <button
              className={scope === "root" ? "active" : ""}
              type="button"
              onClick={() => chooseScope("root")}
            >
              <FolderOpen size={17} />
              <span>根目录</span>
              <small>{overview?.root_count ?? 0}</small>
            </button>
            <p className="favoritesFolderLabel">我的目录</p>
            {overview?.folders.map((folder) => (
              <div className="favoritesFolderRow" key={folder.id}>
                <button
                  type="button"
                  className={scope === folder.id ? "active" : ""}
                  onClick={() => chooseScope(folder.id)}
                >
                  <Folder size={17} />
                  <span>{folder.name}</span>
                  <small>{folder.count}</small>
                </button>
                <FolderMenu folder={folder} edit={editFolder} />
              </div>
            ))}
          </nav>
        </aside>
        <div className="favoritesMain">
          <div className="favoritesListHeading">
            <h2>{title}</h2>
            <span className="mutedText">
              {loading ? "加载中" : `${meta.total} 条`}
            </span>
            {scope !== "all" &&
            scope !== "root" &&
            overview?.folders.find((f) => f.id === scope) ? (
              <FolderMenu
                folder={overview.folders.find((f) => f.id === scope)!}
                edit={editFolder}
              />
            ) : null}
          </div>
          <form
            className="favoritesFilters"
            onSubmit={(e) => {
              e.preventDefault();
              setFilters({ ...draft, keyword: draft.keyword.trim() });
              setPage(1);
            }}
          >
            <label className="favoritesField favoritesSearch">
              搜索
              <input
                maxLength={200}
                placeholder="标题、摘要"
                value={draft.keyword}
                onChange={(e) =>
                  setDraft({ ...draft, keyword: e.target.value })
                }
              />
            </label>
            <label className="favoritesField">
              分类
              <select
                value={draft.category}
                onChange={(e) =>
                  setDraft({ ...draft, category: e.target.value })
                }
              >
                <option value="">全部分类</option>
                {Array.from(
                  new Set([
                    ...(overview?.categories ?? []),
                    ...(draft.category ? [draft.category] : [])
                  ])
                ).map((c) => (
                  <option key={c} value={c}>
                    {favoriteCategoryLabels[c] ?? c}
                  </option>
                ))}
              </select>
            </label>
            <label className="favoritesField">
              来源
              <select
                value={draft.source_type}
                onChange={(e) =>
                  setDraft({ ...draft, source_type: e.target.value })
                }
              >
                <option value="">全部来源</option>
                {Array.from(
                  new Set([
                    ...(overview?.source_types ?? []),
                    ...(draft.source_type ? [draft.source_type] : [])
                  ])
                ).map((s) => (
                  <option key={s} value={s}>
                    {favoriteSourceLabels[s] ?? s}
                  </option>
                ))}
              </select>
            </label>
            <label className="favoritesField">
              排序
              <select
                value={draft.sort}
                onChange={(e) => setDraft({ ...draft, sort: e.target.value })}
              >
                <option value="saved">最近收藏</option>
                <option value="published">最近发布</option>
                <option value="score">分数最高</option>
              </select>
            </label>
            <button type="submit">检索</button>
          </form>
          {error ? (
            <Notice tone="danger">
              {error}{" "}
              <button className="ghostButton" type="button" onClick={refresh}>
                重试
              </button>
            </Notice>
          ) : null}
          <div className="favoritesList" aria-busy={loading}>
            {loading ? (
              <div className="favoritesLoading" role="status">
                正在加载收藏
              </div>
            ) : null}
            {!loading && !error && !entries.length ? (
              <div className="favoritesEmpty">
                <Bookmark size={28} />
                <h3>{filtered ? "无匹配内容" : "暂无收藏"}</h3>
                {filtered ? (
                  <button
                    type="button"
                    className="ghostButton"
                    onClick={() => {
                      setDraft(emptyFilters);
                      setFilters(emptyFilters);
                      setPage(1);
                    }}
                  >
                    清除筛选
                  </button>
                ) : (
                  <a className="ghostLink" href="/library">
                    前往信息库
                  </a>
                )}
              </div>
            ) : null}
            {entries.map((entry) => (
              <article className="favoriteEntry" key={entry.item.id}>
                <div className="favoriteEntryTitle">
                  <button
                    className="favoriteTitleButton"
                    type="button"
                    onClick={() => setSelected(entry)}
                  >
                    {entry.item.title}
                  </button>
                  <FavoriteButton item={entry.item} />
                </div>
                <p className="favoriteSummary">
                  {entry.item.summary_zh ||
                    entry.item.content_snippet ||
                    "暂无摘要"}
                </p>
                <div className="favoriteMeta">
                  <span>{entry.item.source.name}</span>
                  <span>
                    {favoriteCategoryLabels[entry.item.category] ??
                      entry.item.category}
                  </span>
                  <span>{entry.item.score.toFixed(1)} 分</span>
                  <span>
                    发布于{" "}
                    {date(entry.item.published_at || entry.item.collected_at)}
                  </span>
                </div>
                <div className="favoriteEntryFooter">
                  <div className="favoriteMeta">
                    <span>
                      <Folder size={14} />
                      {folderName(entry.folder_id)}
                    </span>
                    <span>收藏于 {date(entry.created_at)}</span>
                  </div>
                  <div className="favoriteEntryActions">
                    <button
                      className="favoriteIconButton"
                      type="button"
                      aria-label={`查看详情：${entry.item.title}`}
                      title="查看详情"
                      onClick={() => setSelected(entry)}
                    >
                      <FileText size={17} />
                    </button>
                    <a
                      className="favoriteIconButton"
                      href={entry.item.url}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`查看原文：${entry.item.title}`}
                      title="查看原文"
                    >
                      <ExternalLink size={17} />
                    </a>
                    <button
                      className="favoriteIconButton"
                      type="button"
                      title="移动或取消收藏"
                      aria-label={`移动或取消收藏：${entry.item.title}`}
                      disabled={!overview || states[entry.item.id] === undefined || !!pending}
                      onClick={() => open(entry.item)}
                    >
                      <MoreHorizontal size={18} />
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
          <PaginationBar
            meta={meta}
            loading={loading}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
          />
        </div>
      </section>
      {selected ? (
        <Modal title="内容详情" drawer onClose={() => setSelected(null)}>
          <div className="favoriteDetail">
            <div className="favoriteMeta">
              <span>{selected.item.source.name}</span>
              <span>{selected.item.score.toFixed(1)} 分</span>
            </div>
            <h3>{selected.item.title}</h3>
            <p>
              {selected.item.summary_zh ||
                selected.item.content_snippet ||
                "暂无摘要"}
            </p>
            {selected.item.importance_zh ? (
              <>
                <h4>为什么重要</h4>
                <p>{selected.item.importance_zh}</p>
              </>
            ) : null}
            <div className="tagList">
              {selected.item.tags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
            <p className="mutedText">
              发布于{" "}
              {date(selected.item.published_at || selected.item.collected_at)}
            </p>
            <div className="favoriteEntryActions">
              <FavoriteButton item={selected.item} />
              <a
                className="linkButton"
                href={selected.item.url}
                target="_blank"
                rel="noreferrer"
              >
                查看原文
                <ExternalLink size={16} />
              </a>
            </div>
          </div>
        </Modal>
      ) : null}
      {folderAction ? (
        <Modal
          title={
            folderAction.mode === "create"
              ? "新建目录"
              : folderAction.mode === "rename"
                ? "重命名目录"
                : "删除目录"
          }
          busy={busy}
          onClose={() => setFolderAction(null)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void submitFolder();
            }}
          >
            {folderAction.mode === "delete" ? (
              <p className="favoritesDeleteCopy">
                删除“{folderAction.folder.name}”？其中的{" "}
                {folderAction.folder.count} 条收藏将移至根目录。
              </p>
            ) : (
              <label className="favoritesField">
                目录名称
                <input
                  autoFocus
                  required
                  maxLength={80}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
            )}
            {actionError ? (
              <p className="favoritesError" role="alert">
                {actionError}
              </p>
            ) : null}
            <footer className="favoritesDialogFooter">
              <button
                className="ghostButton"
                type="button"
                disabled={busy}
                onClick={() => setFolderAction(null)}
              >
                取消
              </button>
              <button
                type="submit"
                disabled={
                  busy || (folderAction.mode !== "delete" && !name.trim())
                }
              >
                {busy
                  ? "处理中"
                  : folderAction.mode === "delete"
                    ? "删除并移至根目录"
                    : "保存"}
              </button>
            </footer>
          </form>
        </Modal>
      ) : null}
    </PageScaffold>
  );
}

function FolderMenu({
  folder,
  edit
}: {
  folder: FavoriteFolder;
  edit: (action: FolderAction) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: PointerEvent) => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        ref.current?.querySelector("button")?.focus();
      }
    };
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);
  return (
    <div className="favoriteFolderMenu" ref={ref}>
      <button
        type="button"
        className="favoriteIconButton"
        title={`管理目录：${folder.name}`}
        aria-label={`管理目录：${folder.name}`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <MoreHorizontal size={17} />
      </button>
      {open ? (
        <div className="favoriteMenuOptions" aria-label="目录操作">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              edit({ mode: "rename", folder });
            }}
          >
            <Pencil size={15} />
            重命名
          </button>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              edit({ mode: "delete", folder });
            }}
          >
            <Trash2 size={15} />
            删除目录
          </button>
        </div>
      ) : null}
    </div>
  );
}

function date(value: string) {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(
    new Date(value)
  );
}
