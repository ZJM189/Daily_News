from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import Text

from app.application.content_library.dtos import (
    LibraryAnalyticsDimensionDTO,
    LibraryAnalyticsDTO,
    LibraryAnalyticsQuery,
    LibraryAnalyticsScoreBucketDTO,
    LibraryAnalyticsTotalsDTO,
    LibraryAnalyticsTrendPointDTO,
    LibraryItemDTO,
    LibraryLLMProviderDTO,
    LibrarySearchQuery,
    LibrarySourceDTO,
)
from app.application.content_library.repositories import ContentLibraryRepository
from app.infrastructure.config import get_settings
from app.infrastructure.models import (
    CategoryCode,
    Item,
    ItemStatus,
    LLMCallLog,
    LLMCallStatus,
    LLMProvider,
    Source,
    SourceType,
)
from app.infrastructure.secrets import SecretCipher

_CATEGORY_LABELS = {
    "model_company": "模型公司",
    "open_source": "开源项目",
    "research_paper": "研究论文",
    "product_launch": "产品发布",
    "community": "社区动态",
    "industry_funding": "产业融资",
    "other": "其他",
}

_SOURCE_TYPE_LABELS = {
    "rss": "RSS",
    "hacker_news": "Hacker News",
    "github": "GitHub",
    "arxiv": "arXiv",
    "product_hunt": "Product Hunt",
    "hugging_face": "Hugging Face",
}

_SCORE_BUCKETS = (
    ("0_40", "0-40", None, 40.0),
    ("40_60", "40-60", 40.0, 60.0),
    ("60_80", "60-80", 60.0, 80.0),
    ("80_plus", "80+", 80.0, None),
)


class SqlAlchemyContentLibraryRepository(ContentLibraryRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_default_llm_provider(self) -> LibraryLLMProviderDTO | None:
        provider = self._session.scalar(
            select(LLMProvider)
            .where(LLMProvider.enabled.is_(True), LLMProvider.is_default.is_(True))
            .limit(1)
        )
        if provider is None:
            return None
        api_key = (
            SecretCipher(get_settings().encryption_key).decrypt(provider.encrypted_api_key)
            if provider.encrypted_api_key
            else None
        )
        return LibraryLLMProviderDTO(
            id=provider.id,
            name=provider.name,
            base_url=provider.base_url,
            model=provider.model,
            api_key=api_key,
            timeout_seconds=provider.timeout_seconds,
            retry_count=provider.retry_count,
        )

    def log_llm_query(
        self,
        *,
        provider: LibraryLLMProviderDTO | None,
        actor_id: UUID,
        status: str,
        latency_ms: int | None,
        error_message: str | None,
    ) -> None:
        self._session.add(
            LLMCallLog(
                provider_id=provider.id if provider else None,
                prompt_version_id=None,
                object_type="library_search_query",
                object_id=actor_id,
                model=provider.model if provider else "unavailable",
                status=LLMCallStatus(status if status in {"success", "failed"} else "failed"),
                input_tokens=None,
                output_tokens=None,
                latency_ms=latency_ms,
                error_message=error_message[:4000] if error_message else None,
            )
        )
        self._session.flush()

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

    def get_analytics(self, *, query: LibraryAnalyticsQuery) -> LibraryAnalyticsDTO:
        conditions = self._build_conditions(query)
        if query.window_days is not None:
            conditions.append(Item.collected_at >= datetime.now(UTC) - timedelta(days=query.window_days))

        return LibraryAnalyticsDTO(
            totals=self._analytics_totals(conditions),
            trend=self._analytics_trend(conditions),
            source_types=self._analytics_source_types(conditions),
            sources=self._analytics_sources(conditions),
            categories=self._analytics_categories(conditions),
            score_buckets=self._analytics_score_buckets(conditions),
        )

    def _build_conditions(
        self, query: LibrarySearchQuery | LibraryAnalyticsQuery
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        search_terms = _search_terms(query)
        if search_terms:
            conditions.append(
                or_(*[_keyword_condition(term) for term in search_terms])
            )
        if query.category is not None:
            conditions.append(Item.category == CategoryCode(query.category))
        if query.source_type is not None:
            conditions.append(Source.type == SourceType(query.source_type))
        if query.source_id is not None:
            conditions.append(Item.source_id == query.source_id)
        if query.status is not None:
            conditions.append(Item.status == ItemStatus(query.status))
        if isinstance(query, LibrarySearchQuery) and query.published_from is not None:
            conditions.append(
                func.coalesce(Item.published_at, Item.collected_at) >= query.published_from
            )
        if isinstance(query, LibrarySearchQuery) and query.published_to is not None:
            conditions.append(
                func.coalesce(Item.published_at, Item.collected_at) <= query.published_to
            )
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

    def _analytics_totals(self, conditions: list[ColumnElement[bool]]) -> LibraryAnalyticsTotalsDTO:
        summarized = and_(Item.summary_zh.is_not(None), Item.summary_zh != "")
        statement = (
            select(
                func.count(Item.id),
                func.count(Item.id).filter(summarized),
                func.count(func.distinct(Item.source_id)),
                func.avg(Item.score),
            )
            .select_from(Item)
            .join(Source)
        )
        if conditions:
            statement = statement.where(*conditions)

        item_count, summarized_count, source_count, average_score = self._session.execute(
            statement
        ).one()
        normalized_item_count = int(item_count or 0)
        normalized_summarized_count = int(summarized_count or 0)
        summary_rate = (
            round((normalized_summarized_count / normalized_item_count) * 100, 1)
            if normalized_item_count
            else 0.0
        )
        return LibraryAnalyticsTotalsDTO(
            item_count=normalized_item_count,
            summarized_count=normalized_summarized_count,
            summary_rate=summary_rate,
            source_count=int(source_count or 0),
            average_score=round(float(average_score or 0), 1),
        )

    def _analytics_trend(
        self, conditions: list[ColumnElement[bool]]
    ) -> list[LibraryAnalyticsTrendPointDTO]:
        collected_date = func.date(Item.collected_at)
        statement = (
            select(collected_date, func.count(Item.id))
            .select_from(Item)
            .join(Source)
            .group_by(collected_date)
            .order_by(collected_date.asc())
        )
        if conditions:
            statement = statement.where(*conditions)

        rows = self._session.execute(statement).all()
        return [
            LibraryAnalyticsTrendPointDTO(date=_coerce_date(collected_at), count=int(count or 0))
            for collected_at, count in rows
        ]

    def _analytics_source_types(
        self, conditions: list[ColumnElement[bool]]
    ) -> list[LibraryAnalyticsDimensionDTO]:
        statement = (
            select(Source.type, func.count(Item.id))
            .select_from(Item)
            .join(Source)
            .group_by(Source.type)
            .order_by(func.count(Item.id).desc(), Source.type.asc())
        )
        if conditions:
            statement = statement.where(*conditions)

        return [
            LibraryAnalyticsDimensionDTO(
                key=source_type,
                label=_SOURCE_TYPE_LABELS.get(source_type, source_type),
                value=int(count or 0),
            )
            for raw_source_type, count in self._session.execute(statement).all()
            for source_type in [_enum_value(raw_source_type)]
        ]

    def _analytics_sources(
        self, conditions: list[ColumnElement[bool]]
    ) -> list[LibraryAnalyticsDimensionDTO]:
        statement = (
            select(Source.id, Source.name, func.count(Item.id))
            .select_from(Item)
            .join(Source)
            .group_by(Source.id, Source.name)
            .order_by(func.count(Item.id).desc(), Source.name.asc())
            .limit(12)
        )
        if conditions:
            statement = statement.where(*conditions)

        return [
            LibraryAnalyticsDimensionDTO(key=str(source_id), label=source_name, value=int(count or 0))
            for source_id, source_name, count in self._session.execute(statement).all()
        ]

    def _analytics_categories(
        self, conditions: list[ColumnElement[bool]]
    ) -> list[LibraryAnalyticsDimensionDTO]:
        statement = (
            select(Item.category, func.count(Item.id))
            .select_from(Item)
            .join(Source)
            .group_by(Item.category)
            .order_by(func.count(Item.id).desc(), Item.category.asc())
        )
        if conditions:
            statement = statement.where(*conditions)

        return [
            LibraryAnalyticsDimensionDTO(
                key=category,
                label=_CATEGORY_LABELS.get(category, category),
                value=int(count or 0),
            )
            for raw_category, count in self._session.execute(statement).all()
            for category in [_enum_value(raw_category)]
        ]

    def _analytics_score_buckets(
        self, conditions: list[ColumnElement[bool]]
    ) -> list[LibraryAnalyticsScoreBucketDTO]:
        buckets: list[LibraryAnalyticsScoreBucketDTO] = []
        for key, label, min_score, max_score in _SCORE_BUCKETS:
            bucket_conditions = list(conditions)
            if min_score is not None:
                bucket_conditions.append(Item.score >= Decimal(str(min_score)))
            if max_score is not None:
                bucket_conditions.append(Item.score < Decimal(str(max_score)))

            statement = select(func.count(Item.id)).select_from(Item).join(Source)
            if bucket_conditions:
                statement = statement.where(*bucket_conditions)
            buckets.append(
                LibraryAnalyticsScoreBucketDTO(
                    key=key,
                    label=label,
                    min_score=min_score,
                    max_score=max_score,
                    value=int(self._session.scalar(statement) or 0),
                )
            )
        return buckets

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


def _enum_value(value: object) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _coerce_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _search_terms(query: LibrarySearchQuery | LibraryAnalyticsQuery) -> tuple[str, ...]:
    terms = [term.strip() for term in query.search_terms if term and term.strip()]
    if query.keyword and query.keyword.strip():
        terms.append(query.keyword.strip())
    result: list[str] = []
    seen: set[str] = set()
    for term in terms:
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(term[:80])
    return tuple(result[:8])


def _keyword_condition(term: str) -> ColumnElement[bool]:
    like_keyword = f"%{term}%"
    return or_(
        Item.title.ilike(like_keyword),
        Item.summary_zh.ilike(like_keyword),
        Item.summary_original.ilike(like_keyword),
        Item.content_snippet.ilike(like_keyword),
        cast(Item.tags, Text).ilike(like_keyword),
    )
