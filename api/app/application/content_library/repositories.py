from typing import Protocol
from uuid import UUID

from app.application.content_library.dtos import (
    LibraryAnalyticsDTO,
    LibraryAnalyticsQuery,
    LibraryItemDTO,
    LibraryLLMProviderDTO,
    LibrarySearchQuery,
)


class ContentLibraryRepository(Protocol):
    def get_default_llm_provider(self) -> LibraryLLMProviderDTO | None:
        raise NotImplementedError

    def log_llm_query(
        self,
        *,
        provider: LibraryLLMProviderDTO | None,
        actor_id: UUID,
        status: str,
        latency_ms: int | None,
        error_message: str | None,
    ) -> None:
        raise NotImplementedError

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
