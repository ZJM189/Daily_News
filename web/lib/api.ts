import type {
  ApiEnvelope,
  Digest,
  FollowingItem,
  JobRun,
  LibraryAnalytics,
  LibraryChatMessage,
  LibraryChatStreamEvent,
  LibraryChatThread,
  LibraryItem,
  LLMProvider,
  NaturalLanguageLibrarySearch,
  Paginated,
  SavedSearch,
  SchedulerConfig,
  Source,
  SourceCredential,
  User,
  UserPreference
} from "./types";

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return ((await response.json()) as ApiEnvelope<T>).data;
}

export async function apiGetEnvelope<T>(path: string): Promise<ApiEnvelope<T>> {
  const response = await fetch(path, {
    credentials: "include",
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as ApiEnvelope<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: JSON_HEADERS,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return ((await response.json()) as ApiEnvelope<T>).data;
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "PUT",
    credentials: "include",
    headers: JSON_HEADERS,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return ((await response.json()) as ApiEnvelope<T>).data;
}

export async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "PATCH",
    credentials: "include",
    headers: JSON_HEADERS,
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return ((await response.json()) as ApiEnvelope<T>).data;
}

export async function login(loginName: string, password: string): Promise<User> {
  const data = await apiPost<{ user: User }>("/api/v1/auth/login", {
    login: loginName,
    password
  });
  return data.user;
}

export function getCurrentUser(): Promise<User> {
  return apiGet<User>("/api/v1/auth/me");
}

export function getTodayDigest(): Promise<Digest | null> {
  return apiGet<Digest | null>("/api/v1/digests/today");
}

export function getDigestByDate(date: string): Promise<Digest | null> {
  return apiGet<Digest | null>(`/api/v1/digests/${date}`);
}

export async function listJobs(page = 1, pageSize = 20): Promise<Paginated<JobRun>> {
  const payload = await apiGetEnvelope<JobRun[]>(
    `/api/v1/admin/jobs?page=${page}&page_size=${pageSize}`
  );
  return {
    data: payload.data,
    meta: {
      page: Number(payload.meta?.page ?? page),
      page_size: Number(payload.meta?.page_size ?? payload.data.length),
      total: Number(payload.meta?.total ?? payload.data.length)
    }
  };
}

export function triggerCollectJob(payload: {
  source_types?: string[];
  source_id?: string;
  since?: string;
}): Promise<JobRun> {
  return apiPost<JobRun>("/api/v1/admin/jobs/collect", {
    source_types: payload.source_types ?? [],
    source_id: payload.source_id,
    since: payload.since
  });
}

export function triggerDailyPipelineJob(payload: {
  source_types?: string[];
  digest_date?: string;
  exclude_recent_digest_days?: number;
  normalize_limit?: number;
  rank_limit?: number;
  topic_limit?: number;
  summarize_limit?: number;
  min_score?: number;
} = {}): Promise<JobRun[]> {
  return apiPost<JobRun[]>("/api/v1/admin/jobs/daily-pipeline", {
    source_types: payload.source_types ?? [],
    digest_date: payload.digest_date,
    exclude_recent_digest_days: payload.exclude_recent_digest_days ?? 3,
    normalize_limit: payload.normalize_limit ?? 5000,
    rank_limit: payload.rank_limit ?? 5000,
    topic_limit: payload.topic_limit ?? 1000,
    summarize_limit: payload.summarize_limit ?? 100,
    min_score: payload.min_score ?? 60
  });
}

export function listUsers(): Promise<User[]> {
  return apiGet<User[]>("/api/v1/admin/users?page=1&page_size=100");
}

export function createUser(payload: {
  username: string;
  email?: string | null;
  display_name?: string | null;
  password: string;
  role: "user" | "admin";
  status: "active" | "disabled";
}): Promise<User> {
  return apiPost<User>("/api/v1/admin/users", payload);
}

export function updateUser(
  userId: string,
  payload: {
    display_name?: string | null;
    role?: "user" | "admin";
    status?: "active" | "disabled";
  }
): Promise<User> {
  return apiPatch<User>(`/api/v1/admin/users/${userId}`, payload);
}

export function resetUserPassword(userId: string, newPassword: string): Promise<{ ok: boolean }> {
  return apiPost<{ ok: boolean }>(`/api/v1/admin/users/${userId}/reset-password`, {
    new_password: newPassword
  });
}

export function listLLMProviders(): Promise<LLMProvider[]> {
  return apiGet<LLMProvider[]>("/api/v1/admin/llm-providers?page=1&page_size=100");
}

export function createLLMProvider(payload: {
  name: string;
  base_url: string;
  model: string;
  api_key?: string | null;
  timeout_seconds: number;
  retry_count: number;
  enabled: boolean;
  is_default: boolean;
}): Promise<LLMProvider> {
  return apiPost<LLMProvider>("/api/v1/admin/llm-providers", payload);
}

export function updateLLMProvider(
  providerId: string,
  payload: {
    name?: string;
    base_url?: string;
    model?: string;
    api_key?: string | null;
    timeout_seconds?: number;
    retry_count?: number;
    enabled?: boolean;
    is_default?: boolean;
  }
): Promise<LLMProvider> {
  return apiPatch<LLMProvider>(`/api/v1/admin/llm-providers/${providerId}`, payload);
}

export function setDefaultLLMProvider(providerId: string): Promise<LLMProvider> {
  return apiPost<LLMProvider>(`/api/v1/admin/llm-providers/${providerId}/set-default`);
}

export function listSources(): Promise<Source[]> {
  return apiGet<Source[]>("/api/v1/admin/sources?page=1&page_size=100");
}

export function createSource(payload: {
  name: string;
  type: string;
  status: string;
  url?: string | null;
  query_config?: Record<string, unknown>;
  credential_id?: string | null;
  credential_env_key?: string | null;
  weight: number;
  language?: string | null;
}): Promise<Source> {
  return apiPost<Source>("/api/v1/admin/sources", payload);
}

export function updateSource(
  sourceId: string,
  payload: {
    name?: string;
    status?: string;
    url?: string | null;
    query_config?: Record<string, unknown>;
    credential_id?: string | null;
    credential_env_key?: string | null;
    weight?: number;
    language?: string | null;
  }
): Promise<Source> {
  return apiPatch<Source>(`/api/v1/admin/sources/${sourceId}`, payload);
}

export function listSourceCredentials(): Promise<SourceCredential[]> {
  return apiGet<SourceCredential[]>("/api/v1/admin/source-credentials?page=1&page_size=100");
}

export function createSourceCredential(payload: {
  name: string;
  source_type: string;
  secret: string;
  status: string;
}): Promise<SourceCredential> {
  return apiPost<SourceCredential>("/api/v1/admin/source-credentials", payload);
}

export function updateSourceCredential(
  credentialId: string,
  payload: {
    name?: string;
    secret?: string;
    status?: string;
  }
): Promise<SourceCredential> {
  return apiPatch<SourceCredential>(`/api/v1/admin/source-credentials/${credentialId}`, payload);
}

export function listSchedulerConfigs(): Promise<SchedulerConfig[]> {
  return apiGet<SchedulerConfig[]>("/api/v1/admin/scheduler/configs?page=1&page_size=100");
}

export function updateSchedulerConfig(
  configId: string,
  payload: {
    name?: string;
    cron_expression?: string;
    timezone?: string;
    enabled?: boolean;
    params?: Record<string, unknown>;
  }
): Promise<SchedulerConfig> {
  return apiPatch<SchedulerConfig>(`/api/v1/admin/scheduler/configs/${configId}`, payload);
}

export async function searchLibraryItems(params: URLSearchParams): Promise<Paginated<LibraryItem>> {
  const payload = await apiGetEnvelope<LibraryItem[]>(`/api/v1/library/items?${params.toString()}`);
  return {
    data: payload.data,
    meta: {
      page: Number(payload.meta?.page ?? 1),
      page_size: Number(payload.meta?.page_size ?? payload.data.length),
      total: Number(payload.meta?.total ?? payload.data.length)
    }
  };
}

export async function naturalLanguageLibrarySearch(
  query: string,
  pageSize = 6
): Promise<NaturalLanguageLibrarySearch> {
  const response = await fetch("/api/v1/library/natural-language-search", {
    method: "POST",
    credentials: "include",
    headers: JSON_HEADERS,
    cache: "no-store",
    body: JSON.stringify({ query, page_size: pageSize })
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return (await response.json()) as NaturalLanguageLibrarySearch;
}

export function listLibraryChatThreads(limit = 20): Promise<LibraryChatThread[]> {
  return apiGet<LibraryChatThread[]>(`/api/v1/library/chat/threads?limit=${limit}`);
}

export function createLibraryChatThread(title?: string): Promise<LibraryChatThread> {
  return apiPost<LibraryChatThread>("/api/v1/library/chat/threads", { title });
}

export function listLibraryChatMessages(threadId: string): Promise<LibraryChatMessage[]> {
  return apiGet<LibraryChatMessage[]>(`/api/v1/library/chat/threads/${threadId}/messages`);
}

export async function streamLibraryChatMessage(
  threadId: string,
  content: string,
  onEvent: (event: LibraryChatStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`/api/v1/library/chat/threads/${threadId}/messages/stream`, {
    method: "POST",
    credentials: "include",
    headers: JSON_HEADERS,
    cache: "no-store",
    signal,
    body: JSON.stringify({ content })
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  if (!response.body) {
    throw new Error("浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let receivedDone = false;

  while (!receivedDone) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const events = buffer.split(/\r?\n\r?\n/);
    buffer = events.pop() ?? "";

    for (const eventText of events) {
      const event = parseLibraryChatStreamEvent(eventText);
      if (!event) continue;
      onEvent(event);
      if (event.event === "done") {
        receivedDone = true;
      }
    }

    if (done) break;
  }

  if (!receivedDone) {
    const trailingEvent = parseLibraryChatStreamEvent(buffer);
    if (trailingEvent) onEvent(trailingEvent);
  }
  await reader.cancel().catch(() => undefined);
}

function parseLibraryChatStreamEvent(rawEvent: string): LibraryChatStreamEvent | null {
  const lines = rawEvent.trim().split(/\r?\n/);
  let eventName: string | null = null;
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (!eventName || !dataLines.length) return null;

  try {
    return {
      event: eventName,
      data: JSON.parse(dataLines.join("\n")) as unknown
    } as LibraryChatStreamEvent;
  } catch {
    return null;
  }
}

export function getLibraryAnalytics(params: URLSearchParams): Promise<LibraryAnalytics> {
  return apiGet<LibraryAnalytics>(`/api/v1/library/analytics?${params.toString()}`);
}

export function getUserPreference(): Promise<UserPreference> {
  return apiGet<UserPreference>("/api/v1/following/preferences");
}

export function saveUserPreference(preference: UserPreference): Promise<UserPreference> {
  return apiPut<UserPreference>("/api/v1/following/preferences", preference);
}

export function listSavedSearches(): Promise<SavedSearch[]> {
  return apiGet<SavedSearch[]>("/api/v1/following/saved-searches");
}

export function createSavedSearch(payload: {
  name: string;
  query: Record<string, unknown>;
  apply_as_filter?: boolean;
  apply_as_boost?: boolean;
  enabled?: boolean;
}): Promise<SavedSearch> {
  return apiPost<SavedSearch>("/api/v1/following/saved-searches", payload);
}

export function updateSavedSearch(
  searchId: string,
  payload: {
    name?: string;
    query?: Record<string, unknown>;
    apply_as_filter?: boolean;
    apply_as_boost?: boolean;
    enabled?: boolean;
  }
): Promise<SavedSearch> {
  return apiPatch<SavedSearch>(`/api/v1/following/saved-searches/${searchId}`, payload);
}

export function deleteSavedSearch(searchId: string): Promise<{ ok: boolean }> {
  return apiDelete<{ ok: boolean }>(`/api/v1/following/saved-searches/${searchId}`);
}

export function createFeedback(payload: {
  action: "more_like" | "less_like" | "block_source";
  item_id?: string;
  source_id?: string;
}): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/api/v1/following/feedback", payload);
}

export async function listFollowingItems(page = 1, pageSize = 20): Promise<Paginated<FollowingItem>> {
  const payload = await apiGetEnvelope<FollowingItem[]>(
    `/api/v1/following/items?page=${page}&page_size=${pageSize}`
  );
  return {
    data: payload.data,
    meta: {
      page: Number(payload.meta?.page ?? page),
      page_size: Number(payload.meta?.page_size ?? payload.data.length),
      total: Number(payload.meta?.total ?? payload.data.length)
    }
  };
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "DELETE",
    credentials: "include",
    headers: JSON_HEADERS
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return ((await response.json()) as ApiEnvelope<T>).data;
}
