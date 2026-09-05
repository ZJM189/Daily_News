from typing import Protocol
from uuid import UUID

from app.application.content_library.dtos import (
    LibraryAnalyticsDTO,
    LibraryAnalyticsQuery,
    LibraryItemDTO,
    LibrarySearchQuery,
)


class ContentLibraryRepository(Protocol):
    def search_items(
        self,
        *,
        query: LibrarySearchQuery,
        page: int,
        page_size: int,
    ) -> tuple[list[LibraryItemDTO], int]:
        raise NotImplementedError

    def get_item(self, item_id: UUID) -> LibraryItemDTO | None:
        raise NotImplementedError

    def get_analytics(self, *, query: LibraryAnalyticsQuery) -> LibraryAnalyticsDTO:
        raise NotImplementedError
