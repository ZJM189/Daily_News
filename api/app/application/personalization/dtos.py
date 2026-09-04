from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from app.application.content_library.dtos import LibraryItemDTO


@dataclass(frozen=True, slots=True)
class UserPreferenceDTO:
    follow_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    follow_categories: list[str] = field(default_factory=list)
    follow_source_types: list[str] = field(default_factory=list)
    disabled_source_types: list[str] = field(default_factory=list)
    blocked_source_ids: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FollowingItemDTO:
    item: LibraryItemDTO
    personalized_score: float
    match_reasons: list[str]


@dataclass(frozen=True, slots=True)
class SavedSearchDTO:
    id: UUID
    name: str
    query: dict[str, Any]
    enabled: bool
    apply_as_filter: bool
    apply_as_boost: bool
    created_at: datetime
    updated_at: datetime
