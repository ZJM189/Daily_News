from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DigestCandidateDTO:
    topic_id: UUID
    title: str
    summary_zh: str | None
    importance_zh: str | None
    category: str
    score: Decimal
    source_count: int
    primary_item_id: UUID | None
    primary_source_type: str | None = None
    primary_source_name: str | None = None
    primary_url: str | None = None
    canonical_url: str | None = None


@dataclass(frozen=True, slots=True)
class DigestDTO:
    id: UUID
    digest_date: date
    version: int
    status: str
    title: str
    overview_zh: str | None
    stats: dict[str, object]
    job_run_id: UUID | None
    generated_at: datetime | None
    published_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DigestItemDTO:
    id: UUID
    item_id: UUID | None
    topic_id: UUID | None
    item_type: str
    rank: int
    score_snapshot: Decimal
    title_snapshot: str
    summary_snapshot_zh: str | None
    importance_snapshot_zh: str | None
    category_snapshot: str
    source_snapshot: dict[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DigestDetailDTO:
    digest: DigestDTO
    items: list[DigestItemDTO]


@dataclass(frozen=True, slots=True)
class GenerateDigestExecutionResult:
    job_run_id: UUID | None
    total_count: int
    success_count: int
    failure_count: int
