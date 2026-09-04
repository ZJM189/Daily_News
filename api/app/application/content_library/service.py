from uuid import UUID

from app.application.content_library.dtos import LibraryItemDTO, LibrarySearchQuery
from app.application.content_library.repositories import ContentLibraryRepository
from app.application.identity.dtos import UserDTO


class ContentLibraryService:
    def __init__(self, repository: ContentLibraryRepository) -> None:
        self._repository = repository

    def search_items(
        self,
        *,
        actor: UserDTO,
        query: LibrarySearchQuery,
        page: int,
        page_size: int,
    ) -> tuple[list[LibraryItemDTO], int]:
        del actor
        normalized_query = LibrarySearchQuery(
            keyword=_clean_text(query.keyword),
            category=query.category,
            source_type=query.source_type,
            source_id=query.source_id,
            status=query.status,
            published_from=query.published_from,
            published_to=query.published_to,
            min_score=query.min_score,
            has_summary=query.has_summary,
            sort=query.sort,
        )
        return self._repository.search_items(
            query=normalized_query,
            page=page,
            page_size=page_size,
        )

    def get_item(self, *, actor: UserDTO, item_id: UUID) -> LibraryItemDTO | None:
        del actor
        return self._repository.get_item(item_id)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
