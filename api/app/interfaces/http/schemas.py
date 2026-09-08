from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str | None
    display_name: str | None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=80)
    password: str = Field(min_length=10, max_length=256)
    role: str = Field(default="user", pattern=r"^(user|admin)$")
    status: str = Field(default="active", pattern=r"^(active|disabled)$")


class UpdateUserRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    role: str | None = Field(default=None, pattern=r"^(user|admin)$")
    status: str | None = Field(default=None, pattern=r"^(active|disabled)$")


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=10, max_length=256)


class PaginatedUsersResponse(BaseModel):
    data: list[UserResponse]
    meta: dict[str, int]


class SourceCredentialResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    secret_masked: str
    status: str
    last_test_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateSourceCredentialRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_type: str = Field(
        pattern=r"^(rss|hacker_news|github|arxiv|product_hunt|hugging_face)$"
    )
    secret: str = Field(min_length=1, max_length=4096)
    status: str = Field(default="active", pattern=r"^(active|disabled|missing|error)$")


class UpdateSourceCredentialRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    secret: str | None = Field(default=None, min_length=1, max_length=4096)
    status: str | None = Field(default=None, pattern=r"^(active|disabled|missing|error)$")


class PaginatedSourceCredentialsResponse(BaseModel):
    data: list[SourceCredentialResponse]
    meta: dict[str, int]


class SourceResponse(BaseModel):
    id: UUID
    name: str
    type: str
    status: str
    url: str | None
    query_config: dict[str, Any]
    credential_id: UUID | None
    credential_env_key: str | None
    weight: int
    language: str | None
    last_fetched_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateSourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(pattern=r"^(rss|hacker_news|github|arxiv|product_hunt|hugging_face)$")
    status: str = Field(default="disabled", pattern=r"^(enabled|disabled|missing_token|error)$")
    url: str | None = Field(default=None, max_length=2048)
    query_config: dict[str, Any] = Field(default_factory=dict)
    credential_id: UUID | None = None
    credential_env_key: str | None = Field(default=None, max_length=120)
    weight: int = Field(default=50, ge=0, le=100)
    language: str | None = Field(default=None, max_length=16)


class UpdateSourceRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = Field(default=None, pattern=r"^(enabled|disabled|missing_token|error)$")
    url: str | None = Field(default=None, max_length=2048)
    query_config: dict[str, Any] | None = None
    credential_id: UUID | None = None
    credential_env_key: str | None = Field(default=None, max_length=120)
    weight: int | None = Field(default=None, ge=0, le=100)
    language: str | None = Field(default=None, max_length=16)


class PaginatedSourcesResponse(BaseModel):
    data: list[SourceResponse]
    meta: dict[str, int]


class LibrarySourceResponse(BaseModel):
    id: UUID
    name: str
    type: str
    url: str | None

    model_config = ConfigDict(from_attributes=True)


class LibraryItemResponse(BaseModel):
    id: UUID
    source: LibrarySourceResponse
    title: str
    url: str
    canonical_url: str | None
    summary_original: str | None
    content_snippet: str | None
    summary_zh: str | None
    importance_zh: str | None
    language: str | None
    category: str
    tags: list[str]
    status: str
    score: float
    published_at: datetime | None
    collected_at: datetime
    summarized_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedLibraryItemsResponse(BaseModel):
    data: list[LibraryItemResponse]
    meta: dict[str, int]


class NaturalLanguageLibrarySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    page_size: int = Field(default=10, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be blank")
        return cleaned


class InterpretedLibraryQueryResponse(BaseModel):
    keyword: str | None = None
    search_terms: list[str] = Field(default_factory=list)
    category: str | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    status: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None
    min_score: float | None = None
    has_summary: bool | None = None
    sort: str
    page_size: int


class LibrarySearchChipResponse(BaseModel):
    key: str
    label: str


class LibrarySearchLLMResponse(BaseModel):
    provider: str
    model: str
    confidence: float


class NaturalLanguageLibrarySearchResponse(BaseModel):
    mode: Literal["llm", "fallback"]
    explanation: str
    interpreted_query: InterpretedLibraryQueryResponse
    chips: list[LibrarySearchChipResponse]
    data: list[LibraryItemResponse]
    meta: dict[str, int]
    library_url: str
    llm: LibrarySearchLLMResponse | None = None


class CreateLibraryChatThreadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LibraryChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content must not be blank")
        return cleaned


class LibraryChatThreadResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LibraryChatMessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    user_id: UUID
    role: Literal["user", "assistant"]
    content: str
    metadata: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LibraryAnalyticsTotalsResponse(BaseModel):
    item_count: int
    summarized_count: int
    summary_rate: float
    source_count: int
    average_score: float

    model_config = ConfigDict(from_attributes=True)


class LibraryAnalyticsTrendPointResponse(BaseModel):
    date: date
    count: int

    model_config = ConfigDict(from_attributes=True)


class LibraryAnalyticsDimensionResponse(BaseModel):
    key: str
    label: str
    value: int

    model_config = ConfigDict(from_attributes=True)


class LibraryAnalyticsScoreBucketResponse(BaseModel):
    key: str
    label: str
    min_score: float | None
    max_score: float | None
    value: int

    model_config = ConfigDict(from_attributes=True)


class LibraryAnalyticsResponse(BaseModel):
    totals: LibraryAnalyticsTotalsResponse
    trend: list[LibraryAnalyticsTrendPointResponse]
    source_types: list[LibraryAnalyticsDimensionResponse]
    sources: list[LibraryAnalyticsDimensionResponse]
    categories: list[LibraryAnalyticsDimensionResponse]
    score_buckets: list[LibraryAnalyticsScoreBucketResponse]

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceResponse(BaseModel):
    follow_keywords: list[str]
    exclude_keywords: list[str]
    follow_categories: list[str]
    follow_source_types: list[str]
    disabled_source_types: list[str]
    blocked_source_ids: list[str]
    blocked_domains: list[str]
    weights: dict[str, float]

    model_config = ConfigDict(from_attributes=True)


class UpdateUserPreferenceRequest(BaseModel):
    follow_keywords: list[str] = Field(default_factory=list, max_length=50)
    exclude_keywords: list[str] = Field(default_factory=list, max_length=50)
    follow_categories: list[
        Literal[
            "model_company",
            "open_source",
            "research_paper",
            "product_launch",
            "community",
            "industry_funding",
            "other",
        ]
    ] = Field(default_factory=list, max_length=20)
    follow_source_types: list[
        Literal["rss", "hacker_news", "github", "arxiv", "product_hunt", "hugging_face"]
    ] = Field(default_factory=list, max_length=20)
    disabled_source_types: list[
        Literal["rss", "hacker_news", "github", "arxiv", "product_hunt", "hugging_face"]
    ] = Field(default_factory=list, max_length=20)
    blocked_source_ids: list[UUID] = Field(default_factory=list, max_length=100)
    blocked_domains: list[str] = Field(default_factory=list, max_length=100)
    weights: dict[str, float] = Field(default_factory=dict)


class FollowingItemResponse(BaseModel):
    item: LibraryItemResponse
    personalized_score: float
    match_reasons: list[str]

    model_config = ConfigDict(from_attributes=True)


class PaginatedFollowingItemsResponse(BaseModel):
    data: list[FollowingItemResponse]
    meta: dict[str, int]


class SavedSearchResponse(BaseModel):
    id: UUID
    name: str
    query: dict[str, Any]
    enabled: bool
    apply_as_filter: bool
    apply_as_boost: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateSavedSearchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: dict[str, Any]
    apply_as_filter: bool = True
    apply_as_boost: bool = True
    enabled: bool = True


class UpdateSavedSearchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    query: dict[str, Any] | None = None
    apply_as_filter: bool | None = None
    apply_as_boost: bool | None = None
    enabled: bool | None = None


class CreateFeedbackRequest(BaseModel):
    action: Literal["more_like", "less_like", "block_source"]
    item_id: UUID | None = None
    source_id: UUID | None = None


class LLMProviderResponse(BaseModel):
    id: UUID
    name: str
    type: str
    base_url: str
    model: str
    api_key_masked: str | None
    timeout_seconds: int
    retry_count: int
    enabled: bool
    is_default: bool
    last_test_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateLLMProviderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=2048)
    model: str = Field(min_length=1, max_length=120)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    retry_count: int = Field(default=2, ge=0, le=10)
    enabled: bool = True
    is_default: bool = False


class UpdateLLMProviderRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, min_length=1, max_length=2048)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    retry_count: int | None = Field(default=None, ge=0, le=10)
    enabled: bool | None = None
    is_default: bool | None = None


class PaginatedLLMProvidersResponse(BaseModel):
    data: list[LLMProviderResponse]
    meta: dict[str, int]


class JobRunResponse(BaseModel):
    id: UUID
    job_type: str
    trigger_type: str
    status: str
    source_id: UUID | None
    parent_job_run_id: UUID | None
    created_by: UUID | None
    params: dict[str, Any]
    total_count: int
    success_count: int
    failure_count: int
    error_message: str | None
    error_detail: dict[str, Any] | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobRunsResponse(BaseModel):
    data: list[JobRunResponse]
    meta: dict[str, int]


class DigestItemResponse(BaseModel):
    id: UUID
    item_id: UUID | None
    topic_id: UUID | None
    item_type: str
    rank: int
    score_snapshot: float
    title_snapshot: str
    summary_snapshot_zh: str | None
    importance_snapshot_zh: str | None
    category_snapshot: str
    source_snapshot: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DigestResponse(BaseModel):
    id: UUID
    digest_date: date
    version: int
    status: str
    title: str
    overview_zh: str | None
    stats: dict[str, Any]
    job_run_id: UUID | None
    generated_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    items: list[DigestItemResponse]

    model_config = ConfigDict(from_attributes=True)


class TriggerCollectRequest(BaseModel):
    source_types: list[str] = Field(default_factory=list)
    source_id: UUID | None = None
    since: datetime | None = None


class TriggerGenerateDigestRequest(BaseModel):
    digest_date: date
    exclude_recent_digest_days: int = Field(default=3, ge=0, le=30)


class TriggerDailyPipelineRequest(BaseModel):
    source_types: list[str] = Field(default_factory=list)
    digest_date: date | None = None
    exclude_recent_digest_days: int = Field(default=3, ge=0, le=30)
    normalize_limit: int = Field(default=5000, ge=1, le=5000)
    rank_limit: int = Field(default=5000, ge=1, le=5000)
    topic_limit: int = Field(default=1000, ge=1, le=5000)
    summarize_limit: int = Field(default=100, ge=1, le=1000)
    min_score: float = Field(default=60, ge=0, le=100)


class TriggerNormalizeRequest(BaseModel):
    source_id: UUID | None = None
    limit: int = Field(default=5000, ge=1, le=5000)
    language: str | None = Field(default=None, max_length=16)


class TriggerRankRequest(BaseModel):
    source_id: UUID | None = None
    limit: int = Field(default=500, ge=1, le=5000)


class TriggerTopicAggregationRequest(BaseModel):
    source_id: UUID | None = None
    limit: int = Field(default=1000, ge=1, le=5000)


class TriggerSummarizeRequest(BaseModel):
    source_id: UUID | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    min_score: float = Field(default=60, ge=0, le=100)


class SchedulerConfigResponse(BaseModel):
    id: UUID
    job_type: str
    name: str
    cron_expression: str
    timezone: str
    enabled: bool
    params: dict[str, Any]
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSchedulerConfigsResponse(BaseModel):
    data: list[SchedulerConfigResponse]
    meta: dict[str, int]


class UpdateSchedulerConfigRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    cron_expression: str | None = Field(default=None, min_length=9, max_length=120)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    enabled: bool | None = None
    params: dict[str, Any] | None = None
