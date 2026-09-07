from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.application.favorites.dtos import (
    FavoriteDTO,
    FavoriteOverviewDTO,
    FavoriteQuery,
    FavoriteStateDTO,
    FolderDTO,
)
from app.domain.favorites.exceptions import FavoriteConflict, FavoriteNotFound
from app.infrastructure.content_library.repositories import SqlAlchemyContentLibraryRepository
from app.infrastructure.models import Favorite, FavoriteFolder, Item, Source, User


class SqlAlchemyFavoritesRepository:
    def __init__(self, session: Session):
        self._session = session

    def _lock_user(self, user_id: UUID):
        # Serialize a user's mutations, including moves racing with folder deletion.
        self._session.execute(select(User.id).where(User.id == user_id).with_for_update()).one()

    def _folder(self, user_id: UUID, folder_id: UUID) -> FavoriteFolder:
        folder = self._session.scalar(
            select(FavoriteFolder).where(
                FavoriteFolder.user_id == user_id,
                FavoriteFolder.id == folder_id,
            )
        )
        if folder is None:
            raise FavoriteNotFound("目录不存在")
        return folder

    def overview(self, user_id: UUID) -> FavoriteOverviewDTO:
        counts = dict(
            self._session.execute(
                select(
                    Favorite.folder_id,
                    func.count(Favorite.id),
                )
                .where(Favorite.user_id == user_id)
                .group_by(Favorite.folder_id)
            ).all()
        )
        folders = self._session.scalars(
            select(FavoriteFolder)
            .where(
                FavoriteFolder.user_id == user_id,
            )
            .order_by(FavoriteFolder.created_at, FavoriteFolder.id)
        ).all()
        dimensions = self._session.execute(
            select(Item.category, Source.type)
            .select_from(Favorite)
            .join(Item, Item.id == Favorite.item_id)
            .join(Source, Source.id == Item.source_id)
            .where(Favorite.user_id == user_id)
            .distinct()
        ).all()
        return FavoriteOverviewDTO(
            folders=[FolderDTO(f.id, f.name, counts.get(f.id, 0)) for f in folders],
            total=sum(counts.values()),
            root_count=counts.get(None, 0),
            categories=sorted({category.value for category, _ in dimensions}),
            source_types=sorted({source.value for _, source in dimensions}),
        )

    def save_folder(self, user_id: UUID, name: str, folder_id: UUID | None) -> FolderDTO:
        self._lock_user(user_id)
        folder = self._folder(user_id, folder_id) if folder_id else None
        duplicate = self._session.scalar(
            select(FavoriteFolder.id).where(
                FavoriteFolder.user_id == user_id,
                FavoriteFolder.name == name,
            )
        )
        if duplicate is not None and duplicate != folder_id:
            raise FavoriteConflict("已存在同名目录")
        if folder is None:
            folder = FavoriteFolder(user_id=user_id, name=name)
            self._session.add(folder)
        else:
            folder.name = name
        self._session.flush()
        count = (
            self._session.scalar(
                select(func.count(Favorite.id)).where(
                    Favorite.user_id == user_id,
                    Favorite.folder_id == folder.id,
                )
            )
            or 0
        )
        return FolderDTO(folder.id, folder.name, count)

    def delete_folder(self, user_id: UUID, folder_id: UUID) -> None:
        self._lock_user(user_id)
        folder = self._folder(user_id, folder_id)
        self._session.execute(
            update(Favorite)
            .where(
                Favorite.user_id == user_id,
                Favorite.folder_id == folder_id,
            )
            .values(folder_id=None)
        )
        self._session.delete(folder)
        self._session.flush()

    def states(self, user_id: UUID, item_ids: list[UUID]) -> list[FavoriteStateDTO]:
        favorites = self._session.scalars(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.item_id.in_(item_ids),
            )
        ).all()
        return [FavoriteStateDTO(f.item_id, f.folder_id, f.created_at) for f in favorites]

    def save(self, user_id: UUID, item_id: UUID, folder_id: UUID | None) -> FavoriteStateDTO:
        self._lock_user(user_id)
        if folder_id is not None:
            self._folder(user_id, folder_id)
        if self._session.get(Item, item_id) is None:
            raise FavoriteNotFound("内容不存在")
        favorite = self._session.scalar(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.item_id == item_id,
            )
        )
        if favorite is None:
            favorite = Favorite(user_id=user_id, item_id=item_id, folder_id=folder_id)
            self._session.add(favorite)
        else:
            favorite.folder_id = folder_id
        self._session.flush()
        return FavoriteStateDTO(favorite.item_id, favorite.folder_id, favorite.created_at)

    def remove(self, user_id: UUID, item_id: UUID) -> None:
        self._lock_user(user_id)
        self._session.execute(
            delete(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.item_id == item_id,
            )
        )

    def search(self, user_id: UUID, query: FavoriteQuery, page: int, page_size: int):
        conditions = [Favorite.user_id == user_id]
        if query.scope == "root":
            conditions.append(Favorite.folder_id.is_(None))
        elif query.scope == "folder":
            self._folder(user_id, query.folder_id)
            conditions.append(Favorite.folder_id == query.folder_id)
        if query.keyword:
            keyword = query.keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append(
                or_(
                    Item.title.ilike(f"%{keyword}%", escape="\\"),
                    Item.summary_zh.ilike(f"%{keyword}%", escape="\\"),
                    Item.content_snippet.ilike(f"%{keyword}%", escape="\\"),
                )
            )
        if query.category:
            conditions.append(Item.category == query.category)
        if query.source_type:
            conditions.append(Source.type == query.source_type)
        statement = (
            select(Favorite, Item, Source)
            .join(
                Item,
                Item.id == Favorite.item_id,
            )
            .join(Source, Source.id == Item.source_id)
            .where(*conditions)
        )
        total = self._session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        sort = {
            "saved": Favorite.created_at,
            "published": func.coalesce(Item.published_at, Item.collected_at),
            "score": Item.score,
        }[query.sort]
        rows = self._session.execute(
            statement.order_by(sort.desc(), Favorite.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        mapper = SqlAlchemyContentLibraryRepository(self._session)
        return [
            FavoriteDTO(mapper._item_to_dto(item, source), f.folder_id, f.created_at)
            for f, item, source in rows
        ], total
