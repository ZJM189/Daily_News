from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.application.content_library.dtos import LibraryItemDTO


@dataclass(frozen=True)
class FolderDTO:
    id: UUID
    name: str
    count: int


@dataclass(frozen=True)
class FavoriteStateDTO:
    item_id: UUID
    folder_id: UUID | None
    created_at: datetime


@dataclass(frozen=True)
class FavoriteDTO:
    item: LibraryItemDTO
    folder_id: UUID | None
    created_at: datetime


@dataclass(frozen=True)
class FavoriteOverviewDTO:
    folders: list[FolderDTO]
    total: int
    root_count: int
    categories: list[str]
    source_types: list[str]


@dataclass(frozen=True)
class FavoriteQuery:
    scope: str = "all"
    folder_id: UUID | None = None
    keyword: str | None = None
    category: str | None = None
    source_type: str | None = None
    sort: str = "saved"
