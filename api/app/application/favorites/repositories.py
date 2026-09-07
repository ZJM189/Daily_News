from typing import Protocol
from uuid import UUID

from app.application.favorites.dtos import (
    FavoriteDTO,
    FavoriteOverviewDTO,
    FavoriteQuery,
    FavoriteStateDTO,
    FolderDTO,
)


class FavoritesRepository(Protocol):
    def overview(self, user_id: UUID) -> FavoriteOverviewDTO: ...

    def save_folder(self, user_id: UUID, name: str, folder_id: UUID | None) -> FolderDTO: ...

    def delete_folder(self, user_id: UUID, folder_id: UUID) -> None: ...

    def states(self, user_id: UUID, item_ids: list[UUID]) -> list[FavoriteStateDTO]: ...

    def save(self, user_id: UUID, item_id: UUID, folder_id: UUID | None) -> FavoriteStateDTO: ...

    def remove(self, user_id: UUID, item_id: UUID) -> None: ...

    def search(
        self,
        user_id: UUID,
        query: FavoriteQuery,
        page: int,
        page_size: int,
    ) -> tuple[list[FavoriteDTO], int]: ...
