import {
  apiDelete,
  apiGet,
  apiGetEnvelope,
  apiPatch,
  apiPost,
  apiPut
} from "./api";
import type { LibraryItem, PageMeta } from "./types";

export type FavoriteFolder = { id: string; name: string; count: number };
export type FavoriteState = {
  item_id: string;
  folder_id: string | null;
  created_at: string;
};
export type FavoriteEntry = {
  item: LibraryItem;
  folder_id: string | null;
  created_at: string;
};
export type FavoriteOverview = {
  folders: FavoriteFolder[];
  total: number;
  root_count: number;
  categories: string[];
  source_types: string[];
};

const base = "/api/v1/favorites";
export const getFavoriteOverview = () =>
  apiGet<FavoriteOverview>(`${base}/folders`);
export const createFavoriteFolder = (name: string) =>
  apiPost<FavoriteFolder>(`${base}/folders`, { name });
export const renameFavoriteFolder = (id: string, name: string) =>
  apiPatch<FavoriteFolder>(`${base}/folders/${id}`, { name });
export const deleteFavoriteFolder = (id: string) =>
  apiDelete(`${base}/folders/${id}`);
export const saveFavorite = (id: string, folderId: string | null) =>
  apiPut<FavoriteState>(`${base}/items/${id}`, { folder_id: folderId });
export const removeFavorite = (id: string) => apiDelete(`${base}/items/${id}`);
export const getFavoriteStates = (ids: string[]) =>
  apiGet<FavoriteState[]>(
    `${base}/status?${new URLSearchParams(ids.map((id) => ["item_ids", id]))}`
  );
export async function searchFavorites(params: URLSearchParams) {
  params = new URLSearchParams(params);
  for (const [key, value] of [...params]) if (!value) params.delete(key);
  const result = await apiGetEnvelope<FavoriteEntry[]>(
    `${base}/items?${params}`
  );
  return { data: result.data, meta: result.meta as PageMeta };
}

export const favoriteCategoryLabels: Record<string, string> = {
  model_company: "模型公司",
  open_source: "开源项目",
  research_paper: "研究论文",
  product_launch: "产品发布",
  community: "社区动态",
  industry_funding: "产业融资",
  other: "其他"
};
export const favoriteSourceLabels: Record<string, string> = {
  rss: "RSS",
  github: "GitHub",
  arxiv: "arXiv",
  hacker_news: "Hacker News",
  product_hunt: "Product Hunt",
  hugging_face: "Hugging Face"
};
