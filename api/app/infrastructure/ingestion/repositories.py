import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.application.ingestion.dtos import (
    CollectableSourceDTO,
    ItemForRankingDTO,
    ItemForSummarizationDTO,
    ItemForTopicAggregationDTO,
    ItemSummaryDTO,
    LLMRuntimeProviderDTO,
    RawCollectedItem,
    RawItemForNormalizationDTO,
    TopicAggregationGroupDTO,
)
from app.application.ingestion.repositories import IngestionRepository
from app.infrastructure.config import get_settings
from app.infrastructure.models import (
    CategoryCode,
    DigestItem,
    Item,
    ItemStatus,
    JobRun,
    JobStatus,
    JobType,
    LLMCallLog,
    LLMCallStatus,
    LLMProvider,
    RawItem,
    Source,
    SourceCredential,
    SourceStatus,
    SourceType,
    Topic,
    TopicItem,
)
from app.infrastructure.secrets import SecretCipher


class SqlAlchemyIngestionRepository(IngestionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def claim_next_collect_job(self) -> UUID | None:
        job_id = self._session.scalar(
            select(JobRun.id)
            .where(JobRun.job_type == JobType.COLLECT, JobRun.status == JobStatus.PENDING)
            .order_by(JobRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return job_id

    def claim_next_normalize_job(self) -> UUID | None:
        job_id = self._session.scalar(
            select(JobRun.id)
            .where(JobRun.job_type == JobType.NORMALIZE, JobRun.status == JobStatus.PENDING)
            .order_by(JobRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return job_id

    def claim_next_rank_job(self) -> UUID | None:
        job_id = self._session.scalar(
            select(JobRun.id)
            .where(JobRun.job_type == JobType.RANK, JobRun.status == JobStatus.PENDING)
            .order_by(JobRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return job_id

    def claim_next_topic_aggregation_job(self) -> UUID | None:
        job_id = self._session.scalar(
            select(JobRun.id)
            .where(JobRun.job_type == JobType.DEDUPE, JobRun.status == JobStatus.PENDING)
            .order_by(JobRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return job_id

    def claim_next_summarize_job(self) -> UUID | None:
        job_id = self._session.scalar(
            select(JobRun.id)
            .where(JobRun.job_type == JobType.SUMMARIZE, JobRun.status == JobStatus.PENDING)
            .order_by(JobRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        return job_id

    def mark_job_running(self, job_run_id: UUID, started_at: datetime) -> None:
        self._session.execute(
            update(JobRun)
            .where(JobRun.id == job_run_id)
            .values(status=JobStatus.RUNNING, started_at=started_at)
        )
        self._session.flush()

    def mark_job_finished(
        self,
        *,
        job_run_id: UUID,
        status: str,
        total_count: int,
        success_count: int,
        failure_count: int,
        error_message: str | None,
        ended_at: datetime,
        duplicate_count: int = 0,
    ) -> None:
        self._session.execute(
            update(JobRun)
            .where(JobRun.id == job_run_id)
            .values(
                status=JobStatus(status),
                total_count=total_count,
                success_count=success_count,
                duplicate_count=duplicate_count,
                failure_count=failure_count,
                error_message=error_message,
                ended_at=ended_at,
            )
        )
        self._session.flush()

    def get_job_params(self, job_run_id: UUID) -> dict[str, object]:
        params = self._session.scalar(select(JobRun.params).where(JobRun.id == job_run_id))
        return params if isinstance(params, dict) else {}

    def list_collectable_sources(
        self,
        *,
        source_types: list[str],
        source_id: UUID | None,
    ) -> list[CollectableSourceDTO]:
        conditions = [Source.status == SourceStatus.ENABLED]
        if source_types:
            conditions.append(
                Source.type.in_([SourceType(source_type) for source_type in source_types])
            )
        if source_id is not None:
            conditions.append(Source.id == source_id)

        sources = self._session.scalars(
            select(Source)
            .where(*conditions)
            .order_by(Source.weight.desc(), Source.created_at.asc())
        ).all()
        return [self._source_to_dto(source) for source in sources]

    def save_raw_items(
        self,
        *,
        source: CollectableSourceDTO,
        job_run_id: UUID,
        items: list[RawCollectedItem],
        fetched_at: datetime,
    ) -> tuple[int, int]:
        inserted_count = 0
        duplicate_count = 0
        for item in items:
            raw_hash = _raw_hash(item.raw_payload)
            if self._raw_item_exists(
                source_id=source.id,
                external_id=item.external_id,
                raw_hash=raw_hash,
            ):
                duplicate_count += 1
                continue

            self._session.add(
                RawItem(
                    source_id=source.id,
                    job_run_id=job_run_id,
                    source_type=SourceType(source.type),
                    external_id=item.external_id,
                    url=item.url,
                    canonical_url=item.canonical_url,
                    title=item.title,
                    author=item.author,
                    published_at=item.published_at,
                    fetched_at=fetched_at,
                    raw_hash=raw_hash,
                    raw_payload=item.raw_payload,
                    status=ItemStatus.COLLECTED,
                )
            )
            inserted_count += 1

        self._session.flush()
        return inserted_count, duplicate_count

    def mark_source_success(self, *, source_id: UUID, fetched_at: datetime) -> None:
        self._session.execute(
            update(Source)
            .where(Source.id == source_id)
            .values(
                last_fetched_at=fetched_at,
                last_success_at=fetched_at,
                last_error=None,
                updated_at=func.now(),
            )
        )
        self._session.flush()

    def mark_source_error(self, *, source_id: UUID, fetched_at: datetime, error: str) -> None:
        self._session.execute(
            update(Source)
            .where(Source.id == source_id)
            .values(last_fetched_at=fetched_at, last_error=error[:4000], updated_at=func.now())
        )
        self._session.flush()

    def list_raw_items_for_normalization(
        self,
        *,
        source_id: UUID | None,
        limit: int,
    ) -> list[RawItemForNormalizationDTO]:
        conditions = [RawItem.status == ItemStatus.COLLECTED]
        if source_id is not None:
            conditions.append(RawItem.source_id == source_id)

        raw_items = self._session.scalars(
            select(RawItem).where(*conditions).order_by(RawItem.fetched_at.asc()).limit(limit)
        ).all()
        return [self._raw_item_to_dto(raw_item) for raw_item in raw_items]

    def create_normalized_item(
        self,
        *,
        raw_item: RawItemForNormalizationDTO,
        normalized_title: str,
        title_hash: str,
        summary_original: str | None,
        content_snippet: str | None,
        tags: list[str],
        metrics: dict[str, object],
        language: str | None,
    ) -> bool:
        if self._item_exists(raw_item=raw_item, title_hash=title_hash):
            return False
        source = self._session.get(Source, raw_item.source_id)
        category = _category_for_source(source)

        self._session.add(
            Item(
                source_id=raw_item.source_id,
                raw_item_id=raw_item.id,
                external_id=raw_item.external_id,
                title=raw_item.title,
                normalized_title=normalized_title,
                title_hash=title_hash,
                url=raw_item.url,
                canonical_url=raw_item.canonical_url,
                summary_original=summary_original,
                content_snippet=content_snippet,
                language=language,
                category=category,
                tags=tags,
                metrics=metrics,
                published_at=raw_item.published_at,
                collected_at=raw_item.fetched_at,
                status=ItemStatus.NORMALIZED,
                score=0,
                score_breakdown={},
            )
        )
        self._session.flush()
        return True

    def mark_raw_item_normalized(self, raw_item_id: UUID) -> None:
        self._mark_raw_item_status(raw_item_id, ItemStatus.NORMALIZED, None)

    def mark_raw_item_deduped(self, raw_item_id: UUID) -> None:
        self._mark_raw_item_status(raw_item_id, ItemStatus.DEDUPED, None)

    def mark_raw_item_failed(self, raw_item_id: UUID, error: str) -> None:
        self._mark_raw_item_status(raw_item_id, ItemStatus.FAILED, error[:4000])

    def list_items_for_ranking(
        self,
        *,
        source_id: UUID | None,
        limit: int,
    ) -> list[ItemForRankingDTO]:
        conditions = [Item.status == ItemStatus.NORMALIZED]
        if source_id is not None:
            conditions.append(Item.source_id == source_id)

        items = self._session.execute(
            select(Item, Source)
            .join(Source, Source.id == Item.source_id)
            .where(*conditions)
            .order_by(Item.published_at.desc().nullslast(), Item.created_at.desc())
            .limit(limit)
        ).all()
        return [self._item_for_ranking_to_dto(item, source) for item, source in items]

    def mark_item_ranked(
        self,
        *,
        item_id: UUID,
        score: float,
        score_breakdown: dict[str, object],
    ) -> None:
        self._session.execute(
            update(Item)
            .where(Item.id == item_id)
            .values(
                score=score,
                score_breakdown=score_breakdown,
                status=ItemStatus.RANKED,
                updated_at=func.now(),
            )
        )
        self._session.flush()

    def mark_item_rank_failed(self, *, item_id: UUID, error: str) -> None:
        self._session.execute(
            update(Item)
            .where(Item.id == item_id)
            .values(status=ItemStatus.FAILED, error_message=error[:4000], updated_at=func.now())
        )
        self._session.flush()

    def list_items_for_topic_aggregation(
        self,
        *,
        source_id: UUID | None,
        limit: int,
        min_score: float,
    ) -> list[ItemForTopicAggregationDTO]:
        conditions = [
            Item.status.in_([ItemStatus.RANKED, ItemStatus.SUMMARIZED]),
            Item.score >= min_score,
        ]
        if source_id is not None:
            conditions.append(Item.source_id == source_id)

        items = self._session.scalars(
            select(Item)
            .where(*conditions)
            .order_by(Item.score.desc(), Item.published_at.desc().nullslast(), Item.created_at.desc())
        ).all()
        balanced_items = select_balanced_items_by_source(items, limit=limit)
        return [self._item_for_topic_aggregation_to_dto(item) for item in balanced_items]

    def upsert_topic_group(self, group: TopicAggregationGroupDTO) -> None:
        topic = self._session.scalar(
            select(Topic)
            .where(Topic.normalized_key == group.normalized_key)
            .order_by(Topic.created_at.asc())
            .limit(1)
        )
        if topic is None and not group.normalized_key.startswith("llm:"):
            topic = self._session.scalar(
                select(Topic)
                .join(TopicItem, TopicItem.topic_id == Topic.id)
                .where(TopicItem.item_id.in_(group.item_ids))
                .order_by(Topic.created_at.asc())
                .limit(1)
            )
        if topic is None:
            topic = Topic(
                title=group.title,
                normalized_key=group.normalized_key,
                category=CategoryCode(group.category),
                tags=group.tags,
                summary_zh=group.summary_zh,
                importance_zh=group.importance_zh,
                score=group.score,
                source_count=group.source_count,
                primary_item_id=group.primary_item_id,
                first_seen_at=group.first_seen_at,
                last_seen_at=group.last_seen_at,
            )
            self._session.add(topic)
            self._session.flush()
        else:
            topic.title = group.title
            topic.category = CategoryCode(group.category)
            topic.tags = group.tags
            topic.summary_zh = group.summary_zh or topic.summary_zh
            topic.importance_zh = group.importance_zh or topic.importance_zh
            topic.score = group.score
            topic.source_count = group.source_count
            topic.primary_item_id = group.primary_item_id
            topic.first_seen_at = group.first_seen_at
            topic.last_seen_at = group.last_seen_at
            topic.updated_at = func.now()
            self._session.flush()

        self._merge_intersecting_topics(topic, group.item_ids)
        self._session.execute(
            update(TopicItem)
            .where(TopicItem.topic_id == topic.id)
            .values(is_primary=False)
        )
        for item_id in group.item_ids:
            topic_item = self._session.get(TopicItem, (topic.id, item_id))
            if topic_item is None:
                self._session.add(
                    TopicItem(
                        topic_id=topic.id,
                        item_id=item_id,
                        relation_type="related",
                        is_primary=item_id == group.primary_item_id,
                    )
                )
            else:
                topic_item.relation_type = "related"
                topic_item.is_primary = item_id == group.primary_item_id
        self._session.flush()

    def get_default_llm_provider(self) -> LLMRuntimeProviderDTO | None:
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
        return LLMRuntimeProviderDTO(
            id=provider.id,
            name=provider.name,
            base_url=provider.base_url,
            model=provider.model,
            api_key=api_key,
            timeout_seconds=provider.timeout_seconds,
            retry_count=provider.retry_count,
        )

    def list_items_for_summarization(
        self,
        *,
        source_id: UUID | None,
        limit: int,
        min_score: float,
    ) -> list[ItemForSummarizationDTO]:
        conditions = [
            Item.status.in_([ItemStatus.RANKED, ItemStatus.FAILED]),
            Item.score >= min_score,
            Item.summary_zh.is_(None),
        ]
        if source_id is not None:
            conditions.append(Item.source_id == source_id)

        items = self._session.scalars(
            select(Item)
            .where(*conditions)
            .order_by(Item.score.desc(), Item.published_at.desc().nullslast(), Item.created_at.desc())
        ).all()
        balanced_items = select_balanced_items_by_source(items, limit=limit)
        return [self._item_for_summarization_to_dto(item) for item in balanced_items]

    def mark_item_summarized(
        self,
        *,
        item_id: UUID,
        provider: LLMRuntimeProviderDTO,
        summary: ItemSummaryDTO,
        prompt_version: str,
    ) -> None:
        self._session.execute(
            update(Item)
            .where(Item.id == item_id)
            .values(
                summary_zh=summary.summary_zh,
                importance_zh=summary.importance_zh,
                tags=summary.tags,
                summary_confidence=summary.confidence,
                summarized_at=func.now(),
                llm_provider_id=provider.id,
                llm_model=provider.model,
                prompt_version=prompt_version,
                status=ItemStatus.SUMMARIZED,
                error_message=None,
                updated_at=func.now(),
            )
        )
        self._session.flush()

    def mark_item_summary_failed(self, *, item_id: UUID, error: str) -> None:
        self._session.execute(
            update(Item)
            .where(Item.id == item_id)
            .values(error_message=error[:4000], updated_at=func.now())
        )
        self._session.flush()

    def log_llm_call(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        object_type: str,
        object_id: UUID,
        status: str,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: int | None,
        error_message: str | None,
    ) -> None:
        self._session.add(
            LLMCallLog(
                provider_id=provider.id,
                prompt_version_id=None,
                object_type=object_type,
                object_id=object_id,
                model=provider.model,
                status=LLMCallStatus(status),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                error_message=error_message[:4000] if error_message else None,
            )
        )
        self._session.flush()

    def _merge_intersecting_topics(self, topic: Topic, item_ids: list[UUID]) -> None:
        duplicate_topics = self._session.scalars(
            select(Topic)
            .join(TopicItem, TopicItem.topic_id == Topic.id)
            .where(TopicItem.item_id.in_(item_ids), Topic.id != topic.id)
        ).all()
        for duplicate in duplicate_topics:
            self._session.execute(
                delete(TopicItem).where(
                    TopicItem.topic_id == duplicate.id,
                    TopicItem.item_id.in_(item_ids),
                )
            )
            has_remaining_items = self._session.scalar(
                select(TopicItem.item_id).where(TopicItem.topic_id == duplicate.id).limit(1)
            )
            is_used_by_digest = self._session.scalar(
                select(DigestItem.id).where(DigestItem.topic_id == duplicate.id).limit(1)
            )
            if has_remaining_items is None and is_used_by_digest is None:
                self._session.delete(duplicate)
        self._session.flush()

    def _raw_item_exists(
        self,
        *,
        source_id: UUID,
        external_id: str | None,
        raw_hash: str,
    ) -> bool:
        conditions = [RawItem.source_id == source_id]
        if external_id:
            conditions.append(or_(RawItem.external_id == external_id, RawItem.raw_hash == raw_hash))
        else:
            conditions.append(RawItem.raw_hash == raw_hash)
        return self._session.scalar(select(RawItem.id).where(*conditions).limit(1)) is not None

    def _source_to_dto(self, source: Source) -> CollectableSourceDTO:
        return CollectableSourceDTO(
            id=source.id,
            name=source.name,
            type=str(source.type.value if hasattr(source.type, "value") else source.type),
            status=str(source.status.value if hasattr(source.status, "value") else source.status),
            url=source.url,
            query_config=source.query_config,
            credential_secret=self._credential_secret(source),
            credential_env_key=source.credential_env_key,
            weight=source.weight,
            language=source.language,
        )

    def _credential_secret(self, source: Source) -> str | None:
        if source.credential_id is None:
            return None
        credential = self._session.get(SourceCredential, source.credential_id)
        if credential is None or credential.status.value != "active":
            return None
        return SecretCipher(get_settings().encryption_key).decrypt(
            credential.encrypted_secret
        )

    def _raw_item_to_dto(self, raw_item: RawItem) -> RawItemForNormalizationDTO:
        return RawItemForNormalizationDTO(
            id=raw_item.id,
            source_id=raw_item.source_id,
            source_type=str(
                raw_item.source_type.value
                if hasattr(raw_item.source_type, "value")
                else raw_item.source_type
            ),
            external_id=raw_item.external_id,
            url=raw_item.url,
            canonical_url=raw_item.canonical_url,
            title=raw_item.title,
            author=raw_item.author,
            published_at=raw_item.published_at,
            fetched_at=raw_item.fetched_at,
            raw_payload=raw_item.raw_payload,
        )

    def _item_for_ranking_to_dto(self, item: Item, source: Source) -> ItemForRankingDTO:
        return ItemForRankingDTO(
            id=item.id,
            source_id=item.source_id,
            source_type=str(source.type.value if hasattr(source.type, "value") else source.type),
            source_weight=source.weight,
            title=item.title,
            summary_original=item.summary_original,
            content_snippet=item.content_snippet,
            tags=list(item.tags or []),
            published_at=item.published_at,
            collected_at=item.collected_at,
        )

    def _item_for_topic_aggregation_to_dto(self, item: Item) -> ItemForTopicAggregationDTO:
        return ItemForTopicAggregationDTO(
            id=item.id,
            source_id=item.source_id,
            title=item.title,
            normalized_title=item.normalized_title,
            url=item.url,
            canonical_url=item.canonical_url,
            summary_original=item.summary_original,
            content_snippet=item.content_snippet,
            summary_zh=item.summary_zh,
            importance_zh=item.importance_zh,
            category=str(item.category.value if hasattr(item.category, "value") else item.category),
            tags=list(item.tags or []),
            score=item.score,
            published_at=item.published_at,
            collected_at=item.collected_at,
        )

    def _item_for_summarization_to_dto(self, item: Item) -> ItemForSummarizationDTO:
        return ItemForSummarizationDTO(
            id=item.id,
            source_id=item.source_id,
            title=item.title,
            url=item.url,
            summary_original=item.summary_original,
            content_snippet=item.content_snippet,
            score=item.score,
            published_at=item.published_at,
        )

    def _item_exists(self, *, raw_item: RawItemForNormalizationDTO, title_hash: str) -> bool:
        conditions = [Item.raw_item_id == raw_item.id]
        if raw_item.external_id:
            conditions.append(
                (Item.source_id == raw_item.source_id) & (Item.external_id == raw_item.external_id)
            )
        if raw_item.canonical_url:
            conditions.append(Item.canonical_url == raw_item.canonical_url)
        conditions.append(Item.title_hash == title_hash)
        return self._session.scalar(select(Item.id).where(or_(*conditions)).limit(1)) is not None

    def _mark_raw_item_status(
        self,
        raw_item_id: UUID,
        status: ItemStatus,
        error_message: str | None,
    ) -> None:
        self._session.execute(
            update(RawItem)
            .where(RawItem.id == raw_item_id)
            .values(status=status, error_message=error_message)
        )
        self._session.flush()


class _BalancedItemLike(Protocol):
    id: UUID
    source_id: UUID
    score: object
    published_at: datetime | None


def select_balanced_items_by_source[TItem: _BalancedItemLike](
    items: list[TItem],
    *,
    limit: int,
    max_per_source: int | None = None,
) -> list[TItem]:
    if limit <= 0 or not items:
        return []

    grouped: dict[UUID, list[TItem]] = defaultdict(list)
    for item in items:
        grouped[item.source_id].append(item)

    for source_items in grouped.values():
        source_items.sort(key=_balanced_item_sort_key, reverse=True)

    ordered_sources = sorted(
        grouped.items(),
        key=lambda entry: _balanced_item_sort_key(entry[1][0]),
        reverse=True,
    )

    selected: list[TItem] = []
    selected_counts: dict[UUID, int] = defaultdict(int)
    cap = max_per_source if max_per_source is not None else max(3, limit // 4)

    for source_id, source_items in ordered_sources[:limit]:
        selected.append(source_items[0])
        selected_counts[source_id] = 1

    while len(selected) < limit:
        best_source_id: UUID | None = None
        best_item: ItemForSummarizationDTO | None = None
        for source_id, source_items in ordered_sources:
            current_count = selected_counts[source_id]
            if current_count >= min(cap, len(source_items)):
                continue
            candidate = source_items[current_count]
            if best_item is None or _balanced_item_sort_key(candidate) > _balanced_item_sort_key(best_item):
                best_source_id = source_id
                best_item = candidate
        if best_item is None or best_source_id is None:
            break
        selected.append(best_item)
        selected_counts[best_source_id] += 1

    return selected


def _balanced_item_sort_key(item: _BalancedItemLike) -> tuple[float, datetime, str]:
    published_at = item.published_at or datetime.min.replace(tzinfo=UTC)
    return float(item.score), published_at, str(item.id)


def _category_for_source(source: Source | None) -> CategoryCode:
    if source is None:
        return CategoryCode.OTHER

    source_type = str(source.type.value if hasattr(source.type, "value") else source.type)
    source_name = (source.name or "").strip().lower()
    source_url = (source.url or "").strip().lower()
    source_text = f"{source_name} {source_url}"

    if source_type == SourceType.ARXIV.value or "arxiv" in source_text:
        return CategoryCode.RESEARCH_PAPER
    if source_type == SourceType.GITHUB.value or "github" in source_text:
        return CategoryCode.OPEN_SOURCE
    if source_type == SourceType.PRODUCT_HUNT.value or "product hunt" in source_text:
        return CategoryCode.PRODUCT_LAUNCH
    if source_type == SourceType.HACKER_NEWS.value:
        return CategoryCode.COMMUNITY
    if source_type == SourceType.HUGGING_FACE.value or "hugging face" in source_text:
        return CategoryCode.OPEN_SOURCE
    if any(marker in source_text for marker in ("openai", "deepmind", "anthropic", "model")):
        return CategoryCode.MODEL_COMPANY
    if any(marker in source_text for marker in ("infoq", "量子位", "qbit")):
        return CategoryCode.COMMUNITY
    return CategoryCode.OTHER


def _raw_hash(payload: dict[str, object]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
