from decimal import Decimal
from uuid import UUID

from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import Text

from app.application.content_library.dtos import (
    LibraryItemDTO,
    LibrarySearchQuery,
    LibrarySourceDTO,
)
from app.application.content_library.repositories import ContentLibraryRepository
from app.infrastructure.models import CategoryCode, Item, ItemStatus, Source, SourceType


class SqlAlchemyContentLibraryRepository(ContentLibraryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def search_items(
        self,
        *,
        query: LibrarySearchQuery,
        page: int,
        page_size: int,
    ) -> tuple[list[LibraryItemDTO], int]:
        conditions = self._build_conditions(query)
        total_statement = select(func.count()).select_from(Item).join(Source)
        list_statement = select(Item, Source).join(Source)

        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self._session.scalar(total_statement) or 0
        rows = self._session.execute(
            list_statement.order_by(*self._sort_expressions(query.sort))
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [self._item_to_dto(item, source) for item, source in rows], total

    def get_item(self, item_id: UUID) -> LibraryItemDTO | None:
        row = self._session.execute(
            select(Item, Source).join(Source).where(Item.id == item_id)
        ).one_or_none()
        if row is None:
            return None
        item, source = row
        return self._item_to_dto(item, source)

    def _build_conditions(self, query: LibrarySearchQuery) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if query.keyword:
            like_keyword = f"%{query.keyword}%"
            conditions.append(
                or_(
                    Item.title.ilike(like_keyword),
                    Item.summary_zh.ilike(like_keyword),
                    Item.summary_original.ilike(like_keyword),
                    Item.content_snippet.ilike(like_keyword),
                    cast(Item.tags, Text).ilike(like_keyword),
                )
            )
        if query.category is not None:
            conditions.append(Item.category == CategoryCode(query.category))
        if query.source_type is not None:
            conditions.append(Source.type == SourceType(query.source_type))
        if query.source_id is not None:
            conditions.append(Item.source_id == query.source_id)
        if query.status is not None:
            conditions.append(Item.status == ItemStatus(query.status))
        if query.published_from is not None:
            conditions.append(func.coalesce(Item.published_at, Item.collected_at) >= query.published_from)
        if query.published_to is not None:
            conditions.append(func.coalesce(Item.published_at, Item.collected_at) <= query.published_to)
        if query.min_score is not None:
            conditions.append(Item.score >= Decimal(str(query.min_score)))
        if query.has_summary is True:
            conditions.append(Item.summary_zh.is_not(None))
            conditions.append(Item.summary_zh != "")
        elif query.has_summary is False:
            conditions.append(or_(Item.summary_zh.is_(None), Item.summary_zh == ""))
        return conditions

    def _sort_expressions(self, sort: str) -> tuple[ColumnElement[object], ...]:
        effective_time = func.coalesce(Item.published_at, Item.collected_at)
        if sort == "score":
            return (Item.score.desc(), effective_time.desc(), Item.created_at.desc())
        if sort == "collected":
            return (Item.collected_at.desc(), Item.created_at.desc())
        return (effective_time.desc(), Item.score.desc(), Item.created_at.desc())

    def _item_to_dto(self, item: Item, source: Source) -> LibraryItemDTO:
        return LibraryItemDTO(
            id=item.id,
            source=LibrarySourceDTO(
                id=source.id,
                name=source.name,
                type=str(source.type.value if hasattr(source.type, "value") else source.type),
                url=source.url,
            ),
            title=item.title,
            url=item.url,
            canonical_url=item.canonical_url,
            summary_original=item.summary_original,
            content_snippet=item.content_snippet,
            summary_zh=item.summary_zh,
            importance_zh=item.importance_zh,
            language=item.language,
            category=str(item.category.value if hasattr(item.category, "value") else item.category),
            tags=item.tags,
            status=str(item.status.value if hasattr(item.status, "value") else item.status),
            score=item.score,
            published_at=item.published_at,
            collected_at=item.collected_at,
            summarized_at=item.summarized_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
