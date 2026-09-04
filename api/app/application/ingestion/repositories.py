from datetime import datetime
from typing import Protocol
from uuid import UUID

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


class IngestionRepository(Protocol):
    def claim_next_collect_job(self) -> UUID | None:
        raise NotImplementedError

    def claim_next_normalize_job(self) -> UUID | None:
        raise NotImplementedError

    def claim_next_rank_job(self) -> UUID | None:
        raise NotImplementedError

    def mark_job_running(self, job_run_id: UUID, started_at: datetime) -> None:
        raise NotImplementedError

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
    ) -> None:
        raise NotImplementedError

    def get_job_params(self, job_run_id: UUID) -> dict[str, object]:
        raise NotImplementedError

    def list_collectable_sources(
        self,
        *,
        source_types: list[str],
        source_id: UUID | None,
    ) -> list[CollectableSourceDTO]:
        raise NotImplementedError

    def save_raw_items(
        self,
        *,
        source: CollectableSourceDTO,
        job_run_id: UUID,
        items: list[RawCollectedItem],
        fetched_at: datetime,
    ) -> tuple[int, int]:
        raise NotImplementedError

    def mark_source_success(self, *, source_id: UUID, fetched_at: datetime) -> None:
        raise NotImplementedError

    def mark_source_error(self, *, source_id: UUID, fetched_at: datetime, error: str) -> None:
        raise NotImplementedError

    def list_raw_items_for_normalization(
        self,
        *,
        source_id: UUID | None,
        limit: int,
    ) -> list[RawItemForNormalizationDTO]:
        raise NotImplementedError

    def create_normalized_item(
        self,
        *,
        raw_item: RawItemForNormalizationDTO,
        normalized_title: str,
        title_hash: str,
        summary_original: str | None,
        content_snippet: str | None,
        language: str | None,
    ) -> bool:
        raise NotImplementedError

    def mark_raw_item_normalized(self, raw_item_id: UUID) -> None:
        raise NotImplementedError

    def mark_raw_item_deduped(self, raw_item_id: UUID) -> None:
        raise NotImplementedError

    def mark_raw_item_failed(self, raw_item_id: UUID, error: str) -> None:
        raise NotImplementedError

    def list_items_for_ranking(
        self,
        *,
        source_id: UUID | None,
        limit: int,
    ) -> list[ItemForRankingDTO]:
        raise NotImplementedError

    def mark_item_ranked(
        self,
        *,
        item_id: UUID,
        score: float,
        score_breakdown: dict[str, object],
    ) -> None:
        raise NotImplementedError

    def mark_item_rank_failed(self, *, item_id: UUID, error: str) -> None:
        raise NotImplementedError

    def claim_next_topic_aggregation_job(self) -> UUID | None:
        raise NotImplementedError

    def claim_next_summarize_job(self) -> UUID | None:
        raise NotImplementedError

    def list_items_for_topic_aggregation(
        self,
        *,
        source_id: UUID | None,
        limit: int,
        min_score: float,
    ) -> list[ItemForTopicAggregationDTO]:
        raise NotImplementedError

    def upsert_topic_group(self, group: TopicAggregationGroupDTO) -> None:
        raise NotImplementedError

    def get_default_llm_provider(self) -> LLMRuntimeProviderDTO | None:
        raise NotImplementedError

    def list_items_for_summarization(
        self,
        *,
        source_id: UUID | None,
        limit: int,
        min_score: float,
    ) -> list[ItemForSummarizationDTO]:
        raise NotImplementedError

    def mark_item_summarized(
        self,
        *,
        item_id: UUID,
        provider: LLMRuntimeProviderDTO,
        summary: ItemSummaryDTO,
        prompt_version: str,
    ) -> None:
        raise NotImplementedError

    def mark_item_summary_failed(self, *, item_id: UUID, error: str) -> None:
        raise NotImplementedError

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
        raise NotImplementedError
