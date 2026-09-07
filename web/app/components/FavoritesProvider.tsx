"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode
} from "react";
import { Bookmark, FolderPlus, X } from "lucide-react";
import {
  createFavoriteFolder,
  getFavoriteOverview,
  getFavoriteStates,
  removeFavorite,
  saveFavorite,
  type FavoriteOverview,
  type FavoriteState
} from "../../lib/favorites";
import { Modal } from "./Modal";

type ItemRef = { id: string; title: string };
type Context = {
  overview: FavoriteOverview | null;
  revision: number;
  states: Record<string, FavoriteState | null>;
  pending: string | null;
  open: (item: ItemRef) => void;
  refresh: () => void;
  loadStates: (ids: string[]) => void;
};
const FavoritesContext = createContext<Context | null>(null);
const messageOf = (err: unknown) =>
  err instanceof Error ? err.message : "操作失败，请重试";

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const [overview, setOverview] = useState<FavoriteOverview | null>(null);
  const [states, setStates] = useState<Record<string, FavoriteState | null>>(
    {}
  );
  const [revision, setRevision] = useState(0);
  const generation = useRef(0);
  const overviewRequest = useRef(0);
  const [pending, setPending] = useState<string | null>(null);
  const [selected, setSelected] = useState<ItemRef | null>(null);
  const [folder, setFolder] = useState("");
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; undoId?: string } | null>(
    null
  );
  const actionLock = useRef(false);

  const loadOverview = useCallback(async () => {
    const request = ++overviewRequest.current;
    try {
      const result = await getFavoriteOverview();
      if (request === overviewRequest.current) {
        setOverview(result);
        setError(null);
      }
    } catch (err) {
      if (request === overviewRequest.current) setError(messageOf(err));
    }
  }, []);
  const refresh = useCallback(() => {
    generation.current++;
    setRevision((value) => value + 1);
    void loadOverview();
  }, [loadOverview]);
  const loadStates = useCallback(async (ids: string[]) => {
    if (!ids.length) return;
    const requestGeneration = generation.current;
    try {
      const result = await getFavoriteStates(ids);
      if (requestGeneration !== generation.current) return;
      const next: Record<string, FavoriteState | null> = Object.fromEntries(
        ids.map((id) => [id, null])
      );
      for (const state of result) next[state.item_id] = state;
      setStates((current) => ({ ...current, ...next }));
    } catch (err) {
      if (requestGeneration === generation.current) setError(messageOf(err));
    }
  }, []);
  useEffect(() => {
    void loadOverview();
    const sync = () => refresh();
    window.addEventListener("focus", sync);
    return () => window.removeEventListener("focus", sync);
  }, [loadOverview, refresh]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(
      () => setToast(null),
      toast.undoId ? 8000 : 3500
    );
    return () => window.clearTimeout(timeout);
  }, [toast]);

  async function persist(item: ItemRef, folderId: string | null, undo = false) {
    if (actionLock.current) return;
    actionLock.current = true;
    setPending(item.id);
    setModalError(null);
    setToast(null);
    generation.current++;
    try {
      const state = await saveFavorite(item.id, folderId);
      setStates((current) => ({ ...current, [item.id]: state }));
      const label =
        overview?.folders.find((f) => f.id === folderId)?.name ?? "根目录";
      setToast({
        text: `已收藏至${label}`,
        undoId: undo ? item.id : undefined
      });
      setSelected(null);
      refresh();
    } catch (err) {
      if (selected) setModalError(messageOf(err));
      else setError(messageOf(err));
    } finally {
      actionLock.current = false;
      setPending(null);
    }
  }
  async function remove(id: string) {
    if (actionLock.current) return;
    actionLock.current = true;
    setPending(id);
    setModalError(null);
    generation.current++;
    try {
      await removeFavorite(id);
      setStates((current) => ({ ...current, [id]: null }));
      setToast({ text: "已取消收藏" });
      setSelected(null);
      refresh();
    } catch (err) {
      if (selected) setModalError(messageOf(err));
      else setError(messageOf(err));
    } finally {
      actionLock.current = false;
      setPending(null);
    }
  }
  function open(item: ItemRef) {
    if (!overview || states[item.id] === undefined || actionLock.current)
      return;
    setError(null);
    setModalError(null);
    if (!states[item.id] && !overview.folders.length) {
      void persist(item, null, true);
      return;
    }
    setFolder(states[item.id]?.folder_id ?? "");
    setQuery("");
    setCreating(false);
    setName("");
    setSelected(item);
  }
  async function createFolder() {
    if (actionLock.current) return;
    actionLock.current = true;
    setPending("folder");
    setModalError(null);
    try {
      const result = await createFavoriteFolder(name.trim());
      setOverview((current) =>
        current
          ? { ...current, folders: [...current.folders, result] }
          : current
      );
      setFolder(result.id);
      setQuery("");
      setCreating(false);
      setName("");
    } catch (err) {
      setModalError(messageOf(err));
    } finally {
      actionLock.current = false;
      setPending(null);
    }
  }
  const existing = selected ? states[selected.id] : null;
  return (
    <FavoritesContext.Provider
      value={{ overview, revision, states, pending, open, refresh, loadStates }}
    >
      {error ? (
        <div className="favoritesBanner" role="alert">
          {error}
          <button className="ghostButton" type="button" onClick={refresh}>
            重试
          </button>
        </div>
      ) : null}
      {children}
      {toast ? (
        <div className="favoritesToast" role="status">
          <span>{toast.text}</span>
          {toast.undoId ? (
            <button
              className="ghostButton"
              type="button"
              disabled={!!pending}
              onClick={() => void remove(toast.undoId!)}
            >
              撤销
            </button>
          ) : null}
          <button
            className="favoriteIconButton"
            type="button"
            title="关闭提示"
            aria-label="关闭提示"
            onClick={() => setToast(null)}
          >
            <X size={16} />
          </button>
        </div>
      ) : null}
      {selected ? (
        <Modal
          title={existing ? "管理收藏" : "收藏到"}
          busy={!!pending}
          onClose={() => setSelected(null)}
        >
          <p className="favoritesSelectedTitle">{selected.title}</p>
          <label className="favoritesField">
            搜索目录
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="目录名称"
            />
          </label>
          <fieldset className="favoritesFolderPicker" disabled={!!pending}>
            <legend className="visuallyHidden">收藏目录</legend>
            <label>
              <input
                type="radio"
                name="favorite-folder"
                value=""
                checked={folder === ""}
                onChange={() => setFolder("")}
              />
              <span>根目录</span>
            </label>
            {overview?.folders
              .filter((f) => f.name.toLowerCase().includes(query.toLowerCase()))
              .map((f) => (
                <label key={f.id}>
                  <input
                    type="radio"
                    name="favorite-folder"
                    value={f.id}
                    checked={folder === f.id}
                    onChange={() => setFolder(f.id)}
                  />
                  <span>{f.name}</span>
                  <small>{f.count}</small>
                </label>
              ))}
            {query &&
            !overview?.folders.some((f) =>
              f.name.toLowerCase().includes(query.toLowerCase())
            ) ? (
              <p className="mutedText">无匹配目录</p>
            ) : null}
          </fieldset>
          {creating ? (
            <form
              className="favoritesInlineForm"
              onSubmit={(e) => {
                e.preventDefault();
                void createFolder();
              }}
            >
              <label className="favoritesField">
                目录名称
                <input
                  autoFocus
                  maxLength={80}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <button type="submit" disabled={!!pending || !name.trim()}>
                创建
              </button>
              <button
                type="button"
                className="ghostButton"
                disabled={!!pending}
                onClick={() => setCreating(false)}
              >
                取消
              </button>
            </form>
          ) : (
            <button
              className="ghostButton"
              type="button"
              disabled={!!pending}
              onClick={() => setCreating(true)}
            >
              <FolderPlus size={16} />
              新建目录
            </button>
          )}
          {modalError ? (
            <p className="favoritesError" role="alert">
              {modalError}
            </p>
          ) : null}
          <footer className="favoritesDialogFooter">
            {existing ? (
              <button
                type="button"
                className="ghostButton favoritesDanger"
                disabled={!!pending}
                onClick={() => void remove(selected.id)}
              >
                取消收藏
              </button>
            ) : null}
            <button
              type="button"
              className="ghostButton"
              disabled={!!pending}
              onClick={() => setSelected(null)}
            >
              取消
            </button>
            <button
              type="button"
              disabled={!!pending || creating}
              onClick={() => void persist(selected, folder || null)}
            >
              {pending ? "保存中" : existing ? "保存位置" : "确认收藏"}
            </button>
          </footer>
        </Modal>
      ) : null}
    </FavoritesContext.Provider>
  );
}

export function useFavorites() {
  const context = useContext(FavoritesContext);
  if (!context) throw new Error("FavoritesProvider is required");
  return context;
}

export function useFavoriteItems(items: ItemRef[]) {
  const { loadStates, revision } = useFavorites();
  const ids = [...new Set(items.map((item) => item.id))].sort().join(",");
  useEffect(() => {
    if (ids) loadStates(ids.split(","));
  }, [ids, loadStates, revision]);
}

export function FavoriteButton({ item }: { item: ItemRef }) {
  const { states, overview, pending, open } = useFavorites();
  const state = states[item.id];
  const folder =
    overview?.folders.find((f) => f.id === state?.folder_id)?.name ?? "根目录";
  const label = state ? `已收藏至${folder}，管理收藏` : "收藏";
  return (
    <button
      type="button"
      className={`favoriteIconButton ${state ? "isSaved" : ""}`}
      title={label}
      aria-label={label}
      aria-pressed={!!state}
      disabled={!overview || state === undefined || !!pending}
      onClick={() => open(item)}
    >
      <Bookmark size={18} fill={state ? "currentColor" : "none"} />
    </button>
  );
}
