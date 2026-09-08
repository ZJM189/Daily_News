from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LibrarySourceDTO:
    id: UUID
    name: str
    type: str
    url: str | None


@dataclass(frozen=True, slots=True)
class LibraryItemDTO:
    id: UUID
    source: LibrarySourceDTO
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
    score: Decimal
    published_at: datetime | None
    collected_at: datetime
    summarized_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LibrarySearchQuery:
    keyword: str | None = None
    search_terms: tuple[str, ...] = ()
    category: str | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    status: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None
    min_score: float | None = None
    has_summary: bool | None = None
    sort: str = "latest"


@dataclass(frozen=True, slots=True)
class LibraryAnalyticsQuery:
    keyword: str | None = None
    search_terms: tuple[str, ...] = ()
    category: str | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    status: str | None = None
    min_score: float | None = None
    has_summary: bool | None = None
    window_days: int | None = 30


@dataclass(frozen=True, slots=True)
class LibraryAnalyticsTotalsDTO:
    item_count: int
    summarized_count: int
    summary_rate: float
    source_count: int
    average_score: float


@dataclass(frozen=True, slots=True)
class LibraryAnalyticsTrendPointDTO:
    date: date
    count: int


@dataclass(frozen=True, slots=True)
class LibraryAnalyticsDimensionDTO:
    key: str
    label: str
    value: int


@dataclass(frozen=True, slots=True)
class LibraryAnalyticsScoreBucketDTO:
    key: str
    label: str
    min_score: float | None
    max_score: float | None
    value: int


@dataclass(frozen=True, slots=True)
class LibraryAnalyticsDTO:
    totals: LibraryAnalyticsTotalsDTO
    trend: list[LibraryAnalyticsTrendPointDTO]
    source_types: list[LibraryAnalyticsDimensionDTO]
    sources: list[LibraryAnalyticsDimensionDTO]
    categories: list[LibraryAnalyticsDimensionDTO]
    score_buckets: list[LibraryAnalyticsScoreBucketDTO]


@dataclass(frozen=True, slots=True)
class LibraryLLMProviderDTO:
    id: UUID
    name: str
    base_url: str
    model: str
    api_key: str | None
    timeout_seconds: int
    retry_count: int


@dataclass(frozen=True, slots=True)
class InterpretedLibraryQueryDTO:
    keyword: str | None = None
    search_terms: tuple[str, ...] = ()
    category: str | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    status: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None
    min_score: float | None = None
    has_summary: bool | None = None
    sort: str = "latest"
    page_size: int = 10


@dataclass(frozen=True, slots=True)
class LibrarySearchChipDTO:
    key: str
    label: str


@dataclass(frozen=True, slots=True)
class LibrarySearchLLMDTO:
    provider: str
    model: str
    confidence: float


@dataclass(frozen=True, slots=True)
class LibraryAgentParseDTO:
    interpreted_query: InterpretedLibraryQueryDTO
    explanation: str
    confidence: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class NaturalLanguageLibrarySearchDTO:
    mode: str
    explanation: str
    interpreted_query: InterpretedLibraryQueryDTO
    chips: list[LibrarySearchChipDTO]
    items: list[LibraryItemDTO]
    total: int
    page: int
    page_size: int
    library_url: str
    llm: LibrarySearchLLMDTO | None = None


@dataclass(frozen=True, slots=True)
class LibraryChatThreadDTO:
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LibraryChatMessageDTO:
    id: UUID
    thread_id: UUID
    user_id: UUID
    role: str
    content: str
    metadata: dict[str, object]
    created_at: datetime
