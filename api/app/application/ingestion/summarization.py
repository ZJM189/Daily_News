from typing import Protocol
from uuid import UUID

from app.application.ingestion.dtos import (
    ItemForSummarizationDTO,
    ItemSummaryDTO,
    LLMRuntimeProviderDTO,
    SummarizeExecutionResult,
)
from app.application.ingestion.repositories import IngestionRepository


class ItemSummarizationClient(Protocol):
    def summarize_item(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        item: ItemForSummarizationDTO,
    ) -> ItemSummaryDTO:
        raise NotImplementedError


class SummarizeJobExecutor:
    def __init__(self, repository: IngestionRepository, client: ItemSummarizationClient) -> None:
        self._repository = repository
        self._client = client

    def run_next_summarize_job(self) -> SummarizeExecutionResult | None:
        job_run_id = self._repository.claim_next_summarize_job()
        if job_run_id is None:
            return None
        return self.run_summarize_job(job_run_id)

    def run_summarize_job(self, job_run_id: UUID) -> SummarizeExecutionResult:
        from datetime import UTC, datetime

        started_at = datetime.now(UTC)
        self._repository.mark_job_running(job_run_id, started_at)

        provider = self._repository.get_default_llm_provider()
        if provider is None:
            self._repository.mark_job_finished(
                job_run_id=job_run_id,
                status="failed",
                total_count=0,
                success_count=0,
                failure_count=1,
                error_message="no enabled default llm provider configured",
                ended_at=datetime.now(UTC),
            )
            return SummarizeExecutionResult(
                job_run_id=job_run_id,
                total_count=0,
                success_count=0,
                failure_count=1,
            )

        params = self._repository.get_job_params(job_run_id)
        source_id = _uuid_or_none(params.get("source_id"))
        limit = _positive_int(params.get("limit"), default=100, maximum=1000)
        min_score = _float_or_default(params.get("min_score"), default=60.0)
        items = self._repository.list_items_for_summarization(
            source_id=source_id,
            limit=limit,
            min_score=min_score,
        )

        success_count = 0
        failure_count = 0
        errors: list[str] = []
        for item in items:
            try:
                summary = self._client.summarize_item(provider=provider, item=item)
                self._repository.mark_item_summarized(
                    item_id=item.id,
                    provider=provider,
                    summary=summary,
                    prompt_version=ITEM_SUMMARY_PROMPT_VERSION,
                )
                self._repository.log_llm_call(
                    provider=provider,
                    object_type="item",
                    object_id=item.id,
                    status="success",
                    input_tokens=summary.input_tokens,
                    output_tokens=summary.output_tokens,
                    latency_ms=summary.latency_ms,
                    error_message=None,
                )
                success_count += 1
            except SummarySchemaError as exc:
                failure_count += 1
                error = str(exc)
                errors.append(f"{item.id}: {error}")
                self._repository.mark_item_summary_failed(item_id=item.id, error=error)
                self._repository.log_llm_call(
                    provider=provider,
                    object_type="item",
                    object_id=item.id,
                    status="schema_error",
                    input_tokens=None,
                    output_tokens=None,
                    latency_ms=None,
                    error_message=error,
                )
            except Exception as exc:  # noqa: BLE001
                failure_count += 1
                error = str(exc)
                errors.append(f"{item.id}: {error}")
                self._repository.mark_item_summary_failed(item_id=item.id, error=error)
                self._repository.log_llm_call(
                    provider=provider,
                    object_type="item",
                    object_id=item.id,
                    status="failed",
                    input_tokens=None,
                    output_tokens=None,
                    latency_ms=None,
                    error_message=error,
                )

        total_count = len(items)
        if errors:
            status = "partial_success" if success_count > 0 else "failed"
        else:
            status = "success"

        self._repository.mark_job_finished(
            job_run_id=job_run_id,
            status=status,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            error_message="; ".join(errors)[:4000] if errors else None,
            ended_at=datetime.now(UTC),
        )
        return SummarizeExecutionResult(
            job_run_id=job_run_id,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
        )


class SummarySchemaError(ValueError):
    pass


def validate_item_summary(payload: dict[str, object]) -> ItemSummaryDTO:
    summary_zh = _required_string(payload.get("summary_zh"), "summary_zh", max_length=1200)
    importance_zh = _required_string(
        payload.get("importance_zh"), "importance_zh", max_length=1200
    )
    tags = _string_list(payload.get("tags"), maximum=12)
    confidence = _confidence(payload.get("confidence"))
    return ItemSummaryDTO(
        summary_zh=summary_zh,
        importance_zh=importance_zh,
        category="other",
        tags=tags,
        confidence=confidence,
        input_tokens=None,
        output_tokens=None,
        latency_ms=None,
    )


def _required_string(value: object, field_name: str, *, max_length: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SummarySchemaError(f"missing required summary field: {field_name}")
    return value.strip()[:max_length]

def _string_list(value: object, *, maximum: int) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        tag = item.strip()[:40]
        key = tag.lower()
        if tag and key not in seen:
            seen.add(key)
            tags.append(tag)
        if len(tags) >= maximum:
            break
    return tags


def _confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return min(max(confidence, 0.0), 1.0)


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


ITEM_SUMMARY_PROMPT_VERSION = "item-summary-zh-v1"
