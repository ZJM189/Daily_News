from dataclasses import dataclass
from datetime import datetime
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
    category: str | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    status: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None
    min_score: float | None = None
    has_summary: bool | None = None
    sort: str = "latest"
