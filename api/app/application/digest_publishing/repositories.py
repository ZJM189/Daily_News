from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.application.digest_publishing.dtos import (
    DigestCandidateDTO,
    DigestDetailDTO,
    DigestDTO,
)


class DigestPublishingRepository(Protocol):
    def claim_next_generate_digest_job(self) -> UUID | None:
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

    def list_digest_topic_candidates(
        self,
        *,
        digest_date: date,
        start_at: datetime,
        end_at: datetime,
        limit: int,
        exclude_recent_digest_days: int,
    ) -> list[DigestCandidateDTO]:
        raise NotImplementedError

    def create_published_digest(
        self,
        *,
        digest_date: date,
        title: str,
        overview_zh: str,
        stats: dict[str, object],
        job_run_id: UUID,
        candidates: list[DigestCandidateDTO],
        generated_at: datetime,
    ) -> DigestDTO:
        raise NotImplementedError

    def get_published_digest(
        self,
        *,
        digest_date: date,
        version: int | None,
    ) -> DigestDetailDTO | None:
        raise NotImplementedError
