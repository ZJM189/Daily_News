from uuid import UUID

from sqlalchemy import cast, func, not_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import Text

from app.application.content_library.dtos import LibraryItemDTO, LibrarySourceDTO
from app.application.personalization.dtos import SavedSearchDTO, UserPreferenceDTO
from app.application.personalization.repositories import PersonalizationRepository
from app.infrastructure.models import (
    CategoryCode,
    FeedbackAction,
    Item,
    ItemStatus,
    SavedSearch,
    Source,
    SourceType,
    UserFeedback,
    UserPreference,
)


class SqlAlchemyPersonalizationRepository(PersonalizationRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_preference(self, user_id: UUID) -> UserPreferenceDTO | None:
        preference = self._session.get(UserPreference, user_id)
        if preference is None:
            return None
        return self._preference_to_dto(preference)

    def save_preference(self, *, user_id: UUID, preference: UserPreferenceDTO) -> UserPreferenceDTO:
        existing = self._session.get(UserPreference, user_id)
        values = {
            "follow_keywords": preference.follow_keywords,
            "exclude_keywords": preference.exclude_keywords,
            "follow_categories": [CategoryCode(value) for value in preference.follow_categories],
            "follow_source_types": [SourceType(value) for value in preference.follow_source_types],
            "disabled_source_types": [SourceType(value) for value in preference.disabled_source_types],
            "blocked_source_ids": [UUID(value) for value in preference.blocked_source_ids],
            "blocked_domains": preference.blocked_domains,
            "weights": preference.weights,
        }
        if existing is None:
            existing = UserPreference(user_id=user_id, **values)
            self._session.add(existing)
        else:
            for key, value in values.items():
                setattr(existing, key, value)
        self._session.flush()
        return self._preference_to_dto(existing)

    def list_saved_searches(self, *, user_id: UUID) -> list[SavedSearchDTO]:
        searches = self._session.scalars(
            select(SavedSearch)
            .where(SavedSearch.user_id == user_id)
            .order_by(SavedSearch.created_at.desc())
        ).all()
        return [self._saved_search_to_dto(search) for search in searches]

    def create_saved_search(
        self,
        *,
        user_id: UUID,
        name: str,
        query: dict[str, object],
        apply_as_filter: bool,
        apply_as_boost: bool,
    ) -> SavedSearchDTO:
        search = SavedSearch(
            user_id=user_id,
            name=name,
            query=query,
            enabled=True,
            apply_as_filter=apply_as_filter,
            apply_as_boost=apply_as_boost,
        )
        self._session.add(search)
        self._session.flush()
        return self._saved_search_to_dto(search)

    def create_feedback(
        self,
        *,
        user_id: UUID,
        action: str,
        item_id: UUID | None,
        source_id: UUID | None,
    ) -> None:
        feedback = UserFeedback(
            user_id=user_id,
            action=FeedbackAction(action),
            item_id=item_id,
            source_id=source_id,
        )
        self._session.add(feedback)
        self._session.flush()

    def list_feed_candidates(
        self,
        *,
        preference: UserPreferenceDTO,
        limit: int,
    ) -> list[LibraryItemDTO]:
        conditions = self._build_conditions(preference)
        effective_time = func.coalesce(Item.published_at, Item.collected_at)
        statement = (
            select(Item, Source)
            .join(Source)
            .where(*conditions)
            .order_by(Item.score.desc(), effective_time.desc(), Item.created_at.desc())
            .limit(limit)
        )
        rows = self._session.execute(statement).all()
        return [self._item_to_dto(item, source) for item, source in rows]

    def _build_conditions(self, preference: UserPreferenceDTO) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Item.status != ItemStatus.FAILED]
        if preference.follow_source_types:
            conditions.append(Source.type.in_([SourceType(value) for value in preference.follow_source_types]))
        if preference.disabled_source_types:
            conditions.append(
                not_(Source.type.in_([SourceType(value) for value in preference.disabled_source_types]))
            )
        if preference.blocked_source_ids:
            conditions.append(not_(Item.source_id.in_([UUID(value) for value in preference.blocked_source_ids])))
        for domain in preference.blocked_domains:
            conditions.append(Item.url.not_ilike(f"%{domain}%"))
        for keyword in preference.exclude_keywords:
            like_keyword = f"%{keyword}%"
            conditions.append(
                not_(
                    or_(
                        Item.title.ilike(like_keyword),
                        Item.summary_zh.ilike(like_keyword),
                        Item.summary_original.ilike(like_keyword),
                        Item.content_snippet.ilike(like_keyword),
                        cast(Item.tags, Text).ilike(like_keyword),
                    )
                )
            )
        return conditions

    def _preference_to_dto(self, preference: UserPreference) -> UserPreferenceDTO:
        return UserPreferenceDTO(
            follow_keywords=preference.follow_keywords,
            exclude_keywords=preference.exclude_keywords,
            follow_categories=[_enum_value(value) for value in preference.follow_categories],
            follow_source_types=[_enum_value(value) for value in preference.follow_source_types],
            disabled_source_types=[_enum_value(value) for value in preference.disabled_source_types],
            blocked_source_ids=[str(value) for value in preference.blocked_source_ids],
            blocked_domains=preference.blocked_domains,
            weights=preference.weights,
        )

    def _saved_search_to_dto(self, search: SavedSearch) -> SavedSearchDTO:
        return SavedSearchDTO(
            id=search.id,
            name=search.name,
            query=search.query,
            enabled=search.enabled,
            apply_as_filter=search.apply_as_filter,
            apply_as_boost=search.apply_as_boost,
            created_at=search.created_at,
            updated_at=search.updated_at,
        )

    def _item_to_dto(self, item: Item, source: Source) -> LibraryItemDTO:
        return LibraryItemDTO(
            id=item.id,
            source=LibrarySourceDTO(
                id=source.id,
                name=source.name,
                type=_enum_value(source.type),
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
            category=_enum_value(item.category),
            tags=item.tags,
            status=_enum_value(item.status),
            score=item.score,
            published_at=item.published_at,
            collected_at=item.collected_at,
            summarized_at=item.summarized_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


def _enum_value(value) -> str:
    return str(value.value if hasattr(value, "value") else value)
