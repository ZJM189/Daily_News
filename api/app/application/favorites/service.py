from uuid import UUID

from app.application.favorites.dtos import (
    FavoriteDTO,
    FavoriteOverviewDTO,
    FavoriteQuery,
    FavoriteStateDTO,
    FolderDTO,
)
from app.application.favorites.repositories import FavoritesRepository
from app.application.identity.dtos import UserDTO


class FavoritesService:
    def __init__(self, repository: FavoritesRepository) -> None:
        self._repository = repository

    def overview(self, actor: UserDTO) -> FavoriteOverviewDTO:
        return self._repository.overview(actor.id)

    def save_folder(self, actor: UserDTO, name: str, folder_id: UUID | None = None) -> FolderDTO:
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("目录名称须为 1 到 80 个字符")
        if name in {"根目录", "全部收藏"}:
            raise ValueError("请使用其他目录名称")
        return self._repository.save_folder(actor.id, name, folder_id)

    def delete_folder(self, actor: UserDTO, folder_id: UUID) -> None:
        self._repository.delete_folder(actor.id, folder_id)

    def states(self, actor: UserDTO, item_ids: list[UUID]) -> list[FavoriteStateDTO]:
        return self._repository.states(actor.id, item_ids)

    def save(self, actor: UserDTO, item_id: UUID, folder_id: UUID | None) -> FavoriteStateDTO:
        return self._repository.save(actor.id, item_id, folder_id)

    def remove(self, actor: UserDTO, item_id: UUID) -> None:
        self._repository.remove(actor.id, item_id)

    def search(
        self,
        actor: UserDTO,
        query: FavoriteQuery,
        page: int,
        page_size: int,
    ) -> tuple[list[FavoriteDTO], int]:
        if query.scope == "folder" and query.folder_id is None:
            raise ValueError("请选择目录")
        return self._repository.search(actor.id, query, page, page_size)
