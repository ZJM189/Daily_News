from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CollectableSourceDTO:
    id: UUID
    name: str
    type: str
    status: str
    url: str | None
    query_config: dict[str, Any]
    credential_env_key: str | None
    weight: int
    language: str | None


@dataclass(frozen=True, slots=True)
class RawCollectedItem:
    external_id: str | None
    url: str
    canonical_url: str | None
    title: str
    author: str | None
    published_at: datetime | None
    raw_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CollectExecutionResult:
    job_run_id: UUID | None
    total_count: int
    success_count: int
    failure_count: int


@dataclass(frozen=True, slots=True)
class RawItemForNormalizationDTO:
    id: UUID
    source_id: UUID
    source_type: str
    external_id: str | None
    url: str
    canonical_url: str | None
    title: str
    author: str | None
    published_at: datetime | None
    fetched_at: datetime
    raw_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NormalizeExecutionResult:
    job_run_id: UUID | None
    total_count: int
    success_count: int
    failure_count: int


@dataclass(frozen=True, slots=True)
class ItemForRankingDTO:
    id: UUID
    source_id: UUID
    source_type: str
    source_weight: int
    title: str
    summary_original: str | None
    content_snippet: str | None
    published_at: datetime | None
    collected_at: datetime


@dataclass(frozen=True, slots=True)
class RankExecutionResult:
    job_run_id: UUID | None
    total_count: int
    success_count: int
    failure_count: int


@dataclass(frozen=True, slots=True)
class ItemForTopicAggregationDTO:
    id: UUID
    source_id: UUID
    title: str
    normalized_title: str
    url: str
    canonical_url: str | None
    summary_original: str | None
    content_snippet: str | None
    summary_zh: str | None
    importance_zh: str | None
    category: str
    tags: list[str]
    score: Decimal
    published_at: datetime | None
    collected_at: datetime


@dataclass(frozen=True, slots=True)
class TopicAggregationGroupDTO:
    normalized_key: str
    title: str
    category: str
    tags: list[str]
    item_ids: list[UUID]
    primary_item_id: UUID
    score: float
    source_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    summary_zh: str | None = None
    importance_zh: str | None = None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class TopicAggregationExecutionResult:
    job_run_id: UUID | None
    total_count: int
    success_count: int
    failure_count: int


@dataclass(frozen=True, slots=True)
class LLMRuntimeProviderDTO:
    id: UUID
    name: str
    base_url: str
    model: str
    api_key: str | None
    timeout_seconds: int
    retry_count: int


@dataclass(frozen=True, slots=True)
class ItemForSummarizationDTO:
    id: UUID
    source_id: UUID
    title: str
    url: str
    summary_original: str | None
    content_snippet: str | None
    score: Decimal
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class ItemSummaryDTO:
    summary_zh: str
    importance_zh: str
    category: str
    tags: list[str]
    confidence: float
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None


@dataclass(frozen=True, slots=True)
class SummarizeExecutionResult:
    job_run_id: UUID | None
    total_count: int
    success_count: int
    failure_count: int
