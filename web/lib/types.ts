export type User = {
  id: string;
  username: string;
  email: string | null;
  display_name: string | null;
  role: "user" | "admin";
  status: "active" | "disabled";
  created_at?: string;
  updated_at?: string;
  last_login_at?: string | null;
};

export type ApiEnvelope<T> = {
  data: T;
  meta?: Record<string, number>;
};

export type PageMeta = {
  page: number;
  page_size: number;
  total: number;
};

export type Paginated<T> = {
  data: T[];
  meta: PageMeta;
};

export type DigestItem = {
  id: string;
  item_id: string | null;
  topic_id: string | null;
  item_type: string;
  rank: number;
  score_snapshot: number;
  title_snapshot: string;
  summary_snapshot_zh: string | null;
  importance_snapshot_zh: string | null;
  category_snapshot: string;
  source_snapshot: Record<string, unknown>;
  created_at: string;
};

export type Digest = {
  id: string;
  digest_date: string;
  version: number;
  status: string;
  title: string;
  overview_zh: string | null;
  stats: Record<string, number>;
  job_run_id: string | null;
  generated_at: string | null;
  published_at: string | null;
  created_at: string;
  items: DigestItem[];
};

export type JobRun = {
  id: string;
  job_type: string;
  trigger_type: string;
  status: string;
  source_id: string | null;
  parent_job_run_id: string | null;
  created_by: string | null;
  params: Record<string, unknown>;
  total_count: number;
  success_count: number;
  duplicate_count: number;
  failure_count: number;
  error_message: string | null;
  error_detail: Record<string, unknown> | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

export type LibrarySource = {
  id: string;
  name: string;
  type: string;
  url: string | null;
};

export type LibraryItem = {
  id: string;
  source: LibrarySource;
  title: string;
  url: string;
  canonical_url: string | null;
  summary_original: string | null;
  content_snippet: string | null;
  summary_zh: string | null;
  importance_zh: string | null;
  language: string | null;
  category: string;
  tags: string[];
  status: string;
  score: number;
  published_at: string | null;
  collected_at: string;
  summarized_at: string | null;
  created_at: string;
  updated_at: string;
};

export type LibraryAnalyticsTotals = {
  item_count: number;
  summarized_count: number;
  summary_rate: number;
  source_count: number;
  average_score: number;
};

export type LibraryAnalyticsTrendPoint = {
  date: string;
  count: number;
};

export type LibraryAnalyticsDimension = {
  key: string;
  label: string;
  value: number;
};

export type LibraryAnalyticsScoreBucket = {
  key: string;
  label: string;
  min_score: number | null;
  max_score: number | null;
  value: number;
};

export type LibraryAnalytics = {
  totals: LibraryAnalyticsTotals;
  trend: LibraryAnalyticsTrendPoint[];
  source_types: LibraryAnalyticsDimension[];
  sources: LibraryAnalyticsDimension[];
  categories: LibraryAnalyticsDimension[];
  score_buckets: LibraryAnalyticsScoreBucket[];
};

export type NaturalLanguageLibrarySearch = {
  mode: "llm" | "fallback";
  explanation: string;
  interpreted_query: {
    keyword: string | null;
    search_terms: string[];
    category: string | null;
    source_type: string | null;
    source_id: string | null;
    status: string | null;
    published_from: string | null;
    published_to: string | null;
    min_score: number | null;
    has_summary: boolean | null;
    sort: string;
    page_size: number;
  };
  chips: Array<{ key: string; label: string }>;
  data: LibraryItem[];
  meta: PageMeta;
  library_url: string;
  llm: {
    provider: string;
    model: string;
    confidence: number;
  } | null;
};

export type LibraryChatThread = {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type LibraryChatMessage = {
  id: string;
  thread_id: string;
  user_id: string;
  role: "user" | "assistant";
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type LibraryChatResultPayload = {
  message_id: string;
  items: LibraryItem[];
  meta: PageMeta;
  library_url: string;
  mode: "llm" | "fallback";
  chips: Array<{ key: string; label: string }>;
  llm: {
    provider: string;
    model: string;
    confidence: number;
  } | null;
};

export type LibraryChatStreamEvent =
  | { event: "status"; data: { message: string; message_id?: string } }
  | { event: "delta"; data: { message_id: string; text: string } }
  | { event: "results"; data: LibraryChatResultPayload }
  | { event: "rejected"; data: { message: string; message_id: string; intent: string } }
  | { event: "error"; data: { message: string; message_id?: string } }
  | { event: "done"; data: { message_id: string } };

export type UserPreference = {
  follow_keywords: string[];
  exclude_keywords: string[];
  follow_categories: string[];
  follow_source_types: string[];
  disabled_source_types: string[];
  blocked_source_ids: string[];
  blocked_domains: string[];
  weights: Record<string, number>;
};

export type FollowingItem = {
  item: LibraryItem;
  personalized_score: number;
  match_reasons: string[];
};

export type SavedSearch = {
  id: string;
  name: string;
  query: Record<string, unknown>;
  enabled: boolean;
  apply_as_filter: boolean;
  apply_as_boost: boolean;
  created_at: string;
  updated_at: string;
};

export type LLMProvider = {
  id: string;
  name: string;
  type: string;
  base_url: string;
  model: string;
  api_key_masked: string | null;
  timeout_seconds: number;
  retry_count: number;
  enabled: boolean;
  is_default: boolean;
  last_test_at: string | null;
  last_test_status: string | null;
  last_test_error: string | null;
  created_at: string;
  updated_at: string;
};

export type Source = {
  id: string;
  name: string;
  type: string;
  status: string;
  url: string | null;
  query_config: Record<string, unknown>;
  credential_id: string | null;
  credential_env_key: string | null;
  weight: number;
  language: string | null;
  last_fetched_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type SourceCredential = {
  id: string;
  name: string;
  source_type: string;
  secret_masked: string;
  status: string;
  last_test_at: string | null;
  last_test_status: string | null;
  last_test_error: string | null;
  created_at: string;
  updated_at: string;
};

export type SchedulerConfig = {
  id: string;
  job_type: string;
  name: string;
  cron_expression: string;
  timezone: string;
  enabled: boolean;
  params: Record<string, unknown>;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
};
