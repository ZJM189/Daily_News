import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.application.ingestion.collectors import CollectorRegistry
from app.application.ingestion.dtos import (
    CollectExecutionResult,
    ItemForRankingDTO,
    NormalizeExecutionResult,
    RankExecutionResult,
)
from app.application.ingestion.repositories import IngestionRepository


class CollectJobExecutor:
    def __init__(
        self,
        repository: IngestionRepository,
        collectors: CollectorRegistry,
    ) -> None:
        self._repository = repository
        self._collectors = collectors

    def run_next_collect_job(self) -> CollectExecutionResult | None:
        job_run_id = self._repository.claim_next_collect_job()
        if job_run_id is None:
            return None
        return self.run_collect_job(job_run_id)

    def run_collect_job(self, job_run_id: UUID) -> CollectExecutionResult:
        started_at = datetime.now().astimezone()
        self._repository.mark_job_running(job_run_id, started_at)

        total_count = 0
        success_count = 0
        failure_count = 0
        errors: list[str] = []

        params = self._repository.get_job_params(job_run_id)
        source_types = _string_list(params.get("source_types"))
        source_id = _uuid_or_none(params.get("source_id"))
        since = _datetime_or_none(params.get("since"))
        sources = self._repository.list_collectable_sources(
            source_types=source_types,
            source_id=source_id,
        )

        for source in sources:
            fetched_at = datetime.now().astimezone()
            collector = self._collectors.get(source.type)
            if collector is None:
                failure_count += 1
                error = f"collector not implemented for source type: {source.type}"
                errors.append(f"{source.name}: {error}")
                self._repository.mark_source_error(
                    source_id=source.id,
                    fetched_at=fetched_at,
                    error=error,
                )
                continue

            try:
                collected_items = collector.collect(source, since=since)
                total_count += len(collected_items)
                inserted_count, _duplicate_count = self._repository.save_raw_items(
                    source=source,
                    job_run_id=job_run_id,
                    items=collected_items,
                    fetched_at=fetched_at,
                )
                success_count += inserted_count
                self._repository.mark_source_success(source_id=source.id, fetched_at=fetched_at)
            # Source isolation: one broken external source must not stop the whole collect job.
            except Exception as exc:  # noqa: BLE001
                failure_count += 1
                error = str(exc)
                errors.append(f"{source.name}: {error}")
                self._repository.mark_source_error(
                    source_id=source.id,
                    fetched_at=fetched_at,
                    error=error,
                )

        if errors:
            status = "partial_success" if success_count > 0 else "failed"
        else:
            status = "success"

        ended_at = datetime.now().astimezone()
        self._repository.mark_job_finished(
            job_run_id=job_run_id,
            status=status,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            error_message="; ".join(errors)[:4000] if errors else None,
            ended_at=ended_at,
        )
        return CollectExecutionResult(
            job_run_id=job_run_id,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
        )


class NormalizeJobExecutor:
    def __init__(self, repository: IngestionRepository) -> None:
        self._repository = repository

    def run_next_normalize_job(self) -> NormalizeExecutionResult | None:
        job_run_id = self._repository.claim_next_normalize_job()
        if job_run_id is None:
            return None
        return self.run_normalize_job(job_run_id)

    def run_normalize_job(self, job_run_id: UUID) -> NormalizeExecutionResult:
        started_at = datetime.now().astimezone()
        self._repository.mark_job_running(job_run_id, started_at)

        params = self._repository.get_job_params(job_run_id)
        source_id = _uuid_or_none(params.get("source_id"))
        limit = _positive_int(params.get("limit"), default=500, maximum=5000)
        raw_items = self._repository.list_raw_items_for_normalization(
            source_id=source_id,
            limit=limit,
        )

        success_count = 0
        duplicate_count = 0
        failure_count = 0
        errors: list[str] = []
        for raw_item in raw_items:
            try:
                normalized_title = normalize_title(raw_item.title)
                created = self._repository.create_normalized_item(
                    raw_item=raw_item,
                    normalized_title=normalized_title,
                    title_hash=hash_title(normalized_title),
                    summary_original=extract_text_field(
                        raw_item.raw_payload,
                        "description",
                        "summary",
                        "content",
                        "encoded",
                    ),
                    content_snippet=extract_text_field(
                        raw_item.raw_payload,
                        "description",
                        "summary",
                        "content",
                        "encoded",
                    ),
                    language=_language_or_default(params.get("language")),
                )
                if created:
                    self._repository.mark_raw_item_normalized(raw_item.id)
                    success_count += 1
                else:
                    self._repository.mark_raw_item_deduped(raw_item.id)
                    duplicate_count += 1
            # Raw item isolation: one malformed payload must not stop the whole normalize job.
            except Exception as exc:  # noqa: BLE001
                failure_count += 1
                error = str(exc)
                errors.append(f"{raw_item.id}: {error}")
                self._repository.mark_raw_item_failed(raw_item.id, error)

        total_count = len(raw_items)
        if errors:
            status = "partial_success" if success_count > 0 or duplicate_count > 0 else "failed"
        else:
            status = "success"

        ended_at = datetime.now().astimezone()
        self._repository.mark_job_finished(
            job_run_id=job_run_id,
            status=status,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            error_message="; ".join(errors)[:4000] if errors else None,
            ended_at=ended_at,
        )
        return NormalizeExecutionResult(
            job_run_id=job_run_id,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
        )


class RankJobExecutor:
    def __init__(self, repository: IngestionRepository) -> None:
        self._repository = repository

    def run_next_rank_job(self) -> RankExecutionResult | None:
        job_run_id = self._repository.claim_next_rank_job()
        if job_run_id is None:
            return None
        return self.run_rank_job(job_run_id)

    def run_rank_job(self, job_run_id: UUID) -> RankExecutionResult:
        started_at = datetime.now().astimezone()
        self._repository.mark_job_running(job_run_id, started_at)

        params = self._repository.get_job_params(job_run_id)
        source_id = _uuid_or_none(params.get("source_id"))
        limit = _positive_int(params.get("limit"), default=500, maximum=5000)
        now = datetime.now(UTC)
        items = self._repository.list_items_for_ranking(source_id=source_id, limit=limit)

        success_count = 0
        failure_count = 0
        errors: list[str] = []
        for item in items:
            try:
                score, breakdown = score_item(item, now=now)
                self._repository.mark_item_ranked(
                    item_id=item.id,
                    score=score,
                    score_breakdown=breakdown,
                )
                success_count += 1
            # Item isolation: one malformed item must not stop the whole rank job.
            except Exception as exc:  # noqa: BLE001
                failure_count += 1
                error = str(exc)
                errors.append(f"{item.id}: {error}")
                self._repository.mark_item_rank_failed(item_id=item.id, error=error)

        total_count = len(items)
        if errors:
            status = "partial_success" if success_count > 0 else "failed"
        else:
            status = "success"

        ended_at = datetime.now().astimezone()
        self._repository.mark_job_finished(
            job_run_id=job_run_id,
            status=status,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            error_message="; ".join(errors)[:4000] if errors else None,
            ended_at=ended_at,
        )
        return RankExecutionResult(
            job_run_id=job_run_id,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _uuid_or_none(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _datetime_or_none(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
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


def _language_or_default(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip().lower()


def hash_title(normalized_title: str) -> str:
    return hashlib.sha256(normalized_title.encode("utf-8")).hexdigest()


def extract_text_field(payload: dict[str, Any], *field_names: str) -> str | None:
    children = payload.get("children")
    if not isinstance(children, dict):
        return None

    for field_name in field_names:
        value = children.get(field_name)
        if not isinstance(value, dict):
            continue
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            return _compact_text(text)
    return None


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()[:4000]


AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "agent",
    "agents",
    "llm",
    "gpt",
    "model",
    "models",
    "openai",
    "anthropic",
    "deepseek",
    "google",
    "gemini",
    "claude",
    "chatgpt",
    "benchmark",
    "research",
    "paper",
    "safety",
    "eval",
    "inference",
    "rag",
}


def score_item(item: ItemForRankingDTO, *, now: datetime) -> tuple[float, dict[str, object]]:
    source_component = round(min(max(item.source_weight, 0), 100) * 0.4, 2)
    recency_component = _recency_component(item.published_at or item.collected_at, now=now)
    keyword_hits = _keyword_hits(item)
    keyword_component = min(len(keyword_hits) * 2.5, 20)
    completeness_component = _completeness_component(item)
    score = round(
        min(
            100,
            source_component
            + recency_component
            + keyword_component
            + completeness_component,
        ),
        2,
    )
    return score, {
        "source_weight": source_component,
        "recency": recency_component,
        "keyword": keyword_component,
        "completeness": completeness_component,
        "keyword_hits": keyword_hits,
    }


def _recency_component(timestamp: datetime, *, now: datetime) -> float:
    comparable_timestamp = timestamp
    if comparable_timestamp.tzinfo is None:
        comparable_timestamp = comparable_timestamp.replace(tzinfo=UTC)
    age_hours = max((now - comparable_timestamp.astimezone(UTC)).total_seconds() / 3600, 0)
    if age_hours <= 24:
        return 30
    if age_hours <= 72:
        return 22
    if age_hours <= 168:
        return 14
    if age_hours <= 720:
        return 8
    return 3


def _keyword_hits(item: ItemForRankingDTO) -> list[str]:
    haystack = " ".join(
        part for part in [item.title, item.summary_original, item.content_snippet] if part
    ).lower()
    return sorted(keyword for keyword in AI_KEYWORDS if keyword in haystack)


def _completeness_component(item: ItemForRankingDTO) -> float:
    score = 0
    if item.summary_original or item.content_snippet:
        score += 6
    if item.published_at is not None:
        score += 4
    if item.title:
        score += 2
    return score
