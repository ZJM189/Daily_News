from typing import Any, Protocol
from uuid import UUID

from app.application.content_library.dtos import LibraryItemDTO
from app.application.personalization.dtos import SavedSearchDTO, UserPreferenceDTO


class PersonalizationRepository(Protocol):
    def get_preference(self, user_id: UUID) -> UserPreferenceDTO | None:
        raise NotImplementedError

    def save_preference(self, *, user_id: UUID, preference: UserPreferenceDTO) -> UserPreferenceDTO:
        raise NotImplementedError

    def list_saved_searches(self, *, user_id: UUID) -> list[SavedSearchDTO]:
        raise NotImplementedError

    def create_saved_search(
        self,
        *,
        user_id: UUID,
        name: str,
        query: dict[str, Any],
        apply_as_filter: bool,
        apply_as_boost: bool,
        enabled: bool,
    ) -> SavedSearchDTO:
        raise NotImplementedError

    def update_saved_search(
        self,
        *,
        user_id: UUID,
        search_id: UUID,
        name: str | None = None,
        query: dict[str, Any] | None = None,
        apply_as_filter: bool | None = None,
        apply_as_boost: bool | None = None,
        enabled: bool | None = None,
    ) -> SavedSearchDTO:
        raise NotImplementedError

    def delete_saved_search(self, *, user_id: UUID, search_id: UUID) -> None:
        raise NotImplementedError

    def create_feedback(
        self,
        *,
        user_id: UUID,
        action: str,
        item_id: UUID | None,
        source_id: UUID | None,
    ) -> None:
        raise NotImplementedError

    def list_feed_candidates(
        self,
        *,
        preference: UserPreferenceDTO,
        limit: int,
    ) -> list[LibraryItemDTO]:
        raise NotImplementedError
