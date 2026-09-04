from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.job_operations.dtos import JobRunDTO, SchedulerConfigDTO


class JobOperationsRepository(Protocol):
    def list_jobs(
        self,
        *,
        job_type: str | None,
        status: str | None,
        source_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[JobRunDTO], int]:
        raise NotImplementedError

    def get_job(self, job_run_id: UUID) -> JobRunDTO | None:
        raise NotImplementedError

    def create_job(
        self,
        *,
        job_type: str,
        trigger_type: str,
        source_id: UUID | None,
        parent_job_run_id: UUID | None,
        created_by: UUID | None,
        params: dict[str, Any],
    ) -> JobRunDTO:
        raise NotImplementedError

    def list_scheduler_configs(
        self,
        *,
        job_type: str | None,
        enabled: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SchedulerConfigDTO], int]:
        raise NotImplementedError

    def get_scheduler_config(self, config_id: UUID) -> SchedulerConfigDTO | None:
        raise NotImplementedError

    def update_scheduler_config(
        self,
        *,
        config_id: UUID,
        name: str | None,
        cron_expression: str | None,
        timezone: str | None,
        enabled: bool | None,
        params: dict[str, Any] | None,
        actor_id: UUID,
    ) -> SchedulerConfigDTO | None:
        raise NotImplementedError

    def ensure_scheduler_config(
        self,
        *,
        job_type: str,
        name: str,
        cron_expression: str,
        timezone: str,
        enabled: bool,
        params: dict[str, Any],
    ) -> SchedulerConfigDTO:
        raise NotImplementedError
