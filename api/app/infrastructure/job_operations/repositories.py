from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.application.job_operations.dtos import JobRunDTO, SchedulerConfigDTO
from app.application.job_operations.repositories import JobOperationsRepository
from app.infrastructure.models import (
    JobRun,
    JobStatus,
    JobTriggerType,
    JobType,
    SchedulerConfig,
)


class SqlAlchemyJobOperationsRepository(JobOperationsRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

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
        conditions = []
        if job_type is not None:
            conditions.append(JobRun.job_type == JobType(job_type))
        if status is not None:
            conditions.append(JobRun.status == JobStatus(status))
        if source_id is not None:
            conditions.append(JobRun.source_id == source_id)
        if created_from is not None:
            conditions.append(JobRun.created_at >= created_from)
        if created_to is not None:
            conditions.append(JobRun.created_at <= created_to)

        total_statement = select(func.count()).select_from(JobRun)
        list_statement = select(JobRun).order_by(JobRun.created_at.desc())
        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self._session.scalar(total_statement) or 0
        jobs = self._session.scalars(
            list_statement.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [self._job_to_dto(job) for job in jobs], total

    def get_job(self, job_run_id: UUID) -> JobRunDTO | None:
        job = self._session.get(JobRun, job_run_id)
        return self._job_to_dto(job) if job is not None else None

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
        job = JobRun(
            job_type=JobType(job_type),
            trigger_type=JobTriggerType(trigger_type),
            status=JobStatus.PENDING,
            source_id=source_id,
            parent_job_run_id=parent_job_run_id,
            created_by=created_by,
            params=params,
        )
        self._session.add(job)
        self._session.flush()
        return self._job_to_dto(job)

    def list_scheduler_configs(
        self,
        *,
        job_type: str | None,
        enabled: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SchedulerConfigDTO], int]:
        conditions = []
        if job_type is not None:
            conditions.append(SchedulerConfig.job_type == JobType(job_type))
        if enabled is not None:
            conditions.append(SchedulerConfig.enabled == enabled)

        total_statement = select(func.count()).select_from(SchedulerConfig)
        list_statement = select(SchedulerConfig).order_by(SchedulerConfig.created_at.desc())
        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self._session.scalar(total_statement) or 0
        configs = self._session.scalars(
            list_statement.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [self._scheduler_config_to_dto(config) for config in configs], total

    def get_scheduler_config(self, config_id: UUID) -> SchedulerConfigDTO | None:
        config = self._session.get(SchedulerConfig, config_id)
        return self._scheduler_config_to_dto(config) if config is not None else None

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
        values: dict[str, object] = {"updated_by": actor_id, "updated_at": func.now()}
        if name is not None:
            values["name"] = name
        if cron_expression is not None:
            values["cron_expression"] = cron_expression
        if timezone is not None:
            values["timezone"] = timezone
        if enabled is not None:
            values["enabled"] = enabled
        if params is not None:
            values["params"] = params

        result = self._session.execute(
            update(SchedulerConfig).where(SchedulerConfig.id == config_id).values(**values)
        )
        if result.rowcount == 0:
            return None
        self._session.flush()
        return self.get_scheduler_config(config_id)

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
        existing = self._session.scalar(
            select(SchedulerConfig).where(SchedulerConfig.job_type == JobType(job_type)).limit(1)
        )
        if existing is not None:
            return self._scheduler_config_to_dto(existing)

        config = SchedulerConfig(
            job_type=JobType(job_type),
            name=name,
            cron_expression=cron_expression,
            timezone=timezone,
            enabled=enabled,
            params=params,
        )
        self._session.add(config)
        self._session.flush()
        return self._scheduler_config_to_dto(config)

    def _job_to_dto(self, job: JobRun) -> JobRunDTO:
        return JobRunDTO(
            id=job.id,
            job_type=str(job.job_type.value if hasattr(job.job_type, "value") else job.job_type),
            trigger_type=str(
                job.trigger_type.value if hasattr(job.trigger_type, "value") else job.trigger_type
            ),
            status=str(job.status.value if hasattr(job.status, "value") else job.status),
            source_id=job.source_id,
            parent_job_run_id=job.parent_job_run_id,
            created_by=job.created_by,
            params=job.params,
            total_count=job.total_count,
            success_count=job.success_count,
            duplicate_count=job.duplicate_count,
            failure_count=job.failure_count,
            error_message=job.error_message,
            error_detail=job.error_detail,
            started_at=job.started_at,
            ended_at=job.ended_at,
            created_at=job.created_at,
        )

    def _scheduler_config_to_dto(self, config: SchedulerConfig) -> SchedulerConfigDTO:
        return SchedulerConfigDTO(
            id=config.id,
            job_type=str(
                config.job_type.value if hasattr(config.job_type, "value") else config.job_type
            ),
            name=config.name,
            cron_expression=config.cron_expression,
            timezone=config.timezone,
            enabled=config.enabled,
            params=config.params,
            created_by=config.created_by,
            updated_by=config.updated_by,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )
