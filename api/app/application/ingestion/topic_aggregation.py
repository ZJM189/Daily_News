import hashlib
import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.application.ingestion.dtos import (
    ItemForTopicAggregationDTO,
    LLMRuntimeProviderDTO,
    TopicAggregationExecutionResult,
    TopicAggregationGroupDTO,
)
from app.application.ingestion.repositories import IngestionRepository


class TopicAggregationClient(Protocol):
    def aggregate_topics(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        items: list[ItemForTopicAggregationDTO],
    ) -> list[TopicAggregationGroupDTO]:
        raise NotImplementedError

    def consolidate_topic_groups(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        groups: list[TopicAggregationGroupDTO],
    ) -> list[TopicAggregationGroupDTO]:
        raise NotImplementedError


class TopicAggregationJobExecutor:
    def __init__(
        self,
        repository: IngestionRepository,
        client: TopicAggregationClient | None = None,
    ) -> None:
        self._repository = repository
        self._client = client

    def run_next_topic_aggregation_job(self) -> TopicAggregationExecutionResult | None:
        job_run_id = self._repository.claim_next_topic_aggregation_job()
        if job_run_id is None:
            return None
        return self.run_topic_aggregation_job(job_run_id)

    def run_topic_aggregation_job(self, job_run_id: UUID) -> TopicAggregationExecutionResult:
        started_at = datetime.now(UTC)
        self._repository.mark_job_running(job_run_id, started_at)

        params = self._repository.get_job_params(job_run_id)
        source_id = _uuid_or_none(params.get("source_id"))
        provider = self._repository.get_default_llm_provider()
        use_llm = provider is not None and self._client is not None
        raw_limit = _positive_int(params.get("limit"), default=200, maximum=5000)
        llm_candidate_limit = _positive_int(
            params.get("llm_candidate_limit"),
            default=200,
            maximum=500,
        )
        limit = min(raw_limit, llm_candidate_limit) if use_llm else raw_limit
        min_score = _float_or_default(params.get("min_score"), default=50.0)
        batch_size = _positive_int(params.get("batch_size"), default=10, maximum=30)
        items = self._repository.list_items_for_topic_aggregation(
            source_id=source_id,
            limit=limit,
            min_score=min_score,
        )
        llm_errors: list[str] = []
        if use_llm:
            groups, llm_errors = aggregate_topic_groups_with_llm(
                provider=provider,
                client=self._client,
                items=items,
                batch_size=batch_size,
            )
        else:
            groups = aggregate_topic_groups(items)

        success_count = 0
        failure_count = 0
        upsert_errors: list[str] = []
        for group in groups:
            try:
                self._repository.upsert_topic_group(group)
                success_count += len(group.item_ids)
            except Exception as exc:  # noqa: BLE001
                failure_count += len(group.item_ids)
                upsert_errors.append(f"{group.normalized_key}: {exc}")

        total_count = len(items)
        if upsert_errors:
            status = "partial_success" if success_count > 0 else "failed"
            error_message = "; ".join([*llm_errors, *upsert_errors])[:4000]
        else:
            status = "success"
            error_message = None

        self._repository.mark_job_finished(
            job_run_id=job_run_id,
            status=status,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            error_message=error_message,
            ended_at=datetime.now(UTC),
        )
        return TopicAggregationExecutionResult(
            job_run_id=job_run_id,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
        )


def aggregate_topic_groups_with_llm(
    *,
    provider: LLMRuntimeProviderDTO,
    client: TopicAggregationClient,
    items: list[ItemForTopicAggregationDTO],
    batch_size: int,
) -> tuple[list[TopicAggregationGroupDTO], list[str]]:
    groups: list[TopicAggregationGroupDTO] = []
    errors: list[str] = []
    for batch_index, batch in enumerate(_chunks(items, batch_size), start=1):
        try:
            batch_groups = client.aggregate_topics(provider=provider, items=batch)
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"llm topic aggregation batch {batch_index} failed, fell back to rules: {exc}"
            )
            batch_groups = aggregate_topic_groups(batch)
        groups.extend(batch_groups)
    if len(groups) > batch_size:
        try:
            groups = client.consolidate_topic_groups(provider=provider, groups=groups)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"llm topic consolidation failed, kept batch topics: {exc}")
    return groups, errors


def aggregate_topic_groups(
    items: Iterable[ItemForTopicAggregationDTO],
) -> list[TopicAggregationGroupDTO]:
    item_list = list(items)
    parents = list(range(len(item_list)))
    key_indexes: dict[str, int] = {}
    for index, item in enumerate(item_list):
        for key in _topic_key_candidates(item):
            previous_index = key_indexes.setdefault(key, index)
            _union(parents, index, previous_index)

    grouped: dict[int, list[ItemForTopicAggregationDTO]] = defaultdict(list)
    for index, item in enumerate(item_list):
        grouped[_find_root(parents, index)].append(item)

    groups = []
    for group in grouped.values():
        groups.append(_build_group(_group_normalized_key(group), group))
    return sorted(groups, key=lambda group: group.normalized_key)


def build_topic_key(item: ItemForTopicAggregationDTO) -> str:
    normalized_title = _normalize_topic_text(item.normalized_title or item.title)
    if len(normalized_title) <= 120:
        return f"title:{normalized_title}"
    return f"title:{hashlib.sha256(normalized_title.encode('utf-8')).hexdigest()}"


def _topic_key_candidates(item: ItemForTopicAggregationDTO) -> list[str]:
    candidates = [build_topic_key(item)]
    keyword_key = _keyword_combination_key(item)
    if keyword_key is not None:
        candidates.append(keyword_key)
    if item.canonical_url:
        canonical_url = _normalize_url(item.canonical_url)
        candidates.append(f"url:{hashlib.sha256(canonical_url.encode('utf-8')).hexdigest()}")
    return candidates


def _keyword_combination_key(item: ItemForTopicAggregationDTO) -> str | None:
    words = _normalize_topic_text(item.normalized_title or item.title).split()
    words = [word for word in words if word not in TOPIC_STOP_WORDS]
    if len(words) < 3:
        return None
    combination = " ".join(sorted(set(words)))
    if len(combination) < 10:
        return None
    return f"keywords:{hashlib.sha256(combination.encode('utf-8')).hexdigest()}"


def _group_normalized_key(items: list[ItemForTopicAggregationDTO]) -> str:
    title_keys = sorted({build_topic_key(item) for item in items})
    return title_keys[0]


def _find_root(parents: list[int], index: int) -> int:
    while parents[index] != index:
        parents[index] = parents[parents[index]]
        index = parents[index]
    return index


def _union(parents: list[int], first: int, second: int) -> None:
    first_root = _find_root(parents, first)
    second_root = _find_root(parents, second)
    if first_root != second_root:
        parents[second_root] = first_root


def _build_group(
    normalized_key: str,
    items: list[ItemForTopicAggregationDTO],
) -> TopicAggregationGroupDTO:
    ordered_items = sorted(
        items,
        key=lambda item: (
            -float(item.score),
            -_timestamp(item.published_at or item.collected_at),
            str(item.id),
        ),
    )
    primary = ordered_items[0]
    timestamps = [item.published_at or item.collected_at for item in items]
    source_count = len({item.source_id for item in items})
    item_count_bonus = min((len(items) - 1) * 1.0, 10.0)
    source_count_bonus = min((source_count - 1) * 3.0, 15.0)
    score = round(min(100.0, float(primary.score) + item_count_bonus + source_count_bonus), 2)

    tags: list[str] = []
    seen_tags: set[str] = set()
    for item in ordered_items:
        for tag in item.tags:
            normalized_tag = tag.strip()
            if normalized_tag and normalized_tag.lower() not in seen_tags:
                seen_tags.add(normalized_tag.lower())
                tags.append(normalized_tag)

    return TopicAggregationGroupDTO(
        normalized_key=normalized_key,
        title=primary.title,
        category=primary.category,
        tags=tags[:30],
        item_ids=[item.id for item in ordered_items],
        primary_item_id=primary.id,
        score=score,
        source_count=source_count,
        first_seen_at=min(timestamps),
        last_seen_at=max(timestamps),
        summary_zh=primary.summary_zh,
        importance_zh=primary.importance_zh,
    )


def _normalize_topic_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\u4e00-\u9fff]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/").lower()


def _timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.timestamp()


def _uuid_or_none(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _positive_int(value: object, *, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < 1:
        return default
    return min(number, maximum)


def _float_or_default(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _chunks(
    items: list[ItemForTopicAggregationDTO],
    size: int,
) -> Iterable[list[ItemForTopicAggregationDTO]]:
    chunk_size = max(size, 1)
    for index in range(0, len(items), chunk_size):
        yield items[index : index + chunk_size]


TOPIC_STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "into",
    "new",
    "of",
    "on",
    "the",
    "to",
    "with",
}
