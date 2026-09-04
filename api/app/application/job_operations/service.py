from datetime import date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.triggers.cron import CronTrigger

from app.application.identity.dtos import UserDTO
from app.application.job_operations.dtos import JobRunDTO, SchedulerConfigDTO
from app.application.job_operations.repositories import JobOperationsRepository
from app.domain.identity.exceptions import PermissionDenied
from app.domain.job_operations.exceptions import (
    InvalidCronExpression,
    InvalidTimezone,
    JobRunNotFound,
    SchedulerConfigNotFound,
)


class JobOperationsService:
    def __init__(self, repository: JobOperationsRepository) -> None:
        self._repository = repository

    def list_jobs(
        self,
        *,
        actor: UserDTO,
        job_type: str | None,
        status: str | None,
        source_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[JobRunDTO], int]:
        self._require_admin(actor)
        return self._repository.list_jobs(
            job_type=job_type,
            status=status,
            source_id=source_id,
            created_from=created_from,
            created_to=created_to,
            page=page,
            page_size=page_size,
        )

    def get_job(self, *, actor: UserDTO, job_run_id: UUID) -> JobRunDTO:
        self._require_admin(actor)
        job = self._repository.get_job(job_run_id)
        if job is None:
            raise JobRunNotFound("job run not found")
        return job

    def retry_job(self, *, actor: UserDTO, job_run_id: UUID) -> JobRunDTO:
        self._require_admin(actor)
        parent = self._repository.get_job(job_run_id)
        if parent is None:
            raise JobRunNotFound("job run not found")
        return self._repository.create_job(
            job_type=parent.job_type,
            trigger_type="retry",
            source_id=parent.source_id,
            parent_job_run_id=parent.id,
            created_by=actor.id,
            params=parent.params,
        )

    def trigger_collect(
        self,
        *,
        actor: UserDTO,
        source_types: list[str],
        since: datetime | None,
        source_id: UUID | None,
    ) -> JobRunDTO:
        self._require_admin(actor)
        params: dict[str, Any] = {"source_types": source_types}
        if since is not None:
            params["since"] = since.isoformat()
        if source_id is not None:
            params["source_id"] = str(source_id)
        return self._repository.create_job(
            job_type="collect",
            trigger_type="manual",
            source_id=source_id,
            parent_job_run_id=None,
            created_by=actor.id,
            params=params,
        )

    def trigger_generate_digest(
        self,
        *,
        actor: UserDTO,
        digest_date: date,
        exclude_recent_digest_days: int = 3,
    ) -> JobRunDTO:
        self._require_admin(actor)
        return self._repository.create_job(
            job_type="generate_digest",
            trigger_type="manual",
            source_id=None,
            parent_job_run_id=None,
            created_by=actor.id,
            params={
                "digest_date": digest_date.isoformat(),
                "exclude_recent_digest_days": max(exclude_recent_digest_days, 0),
            },
        )

    def trigger_daily_pipeline(
        self,
        *,
        actor: UserDTO,
        source_types: list[str],
        digest_date: date | None,
        exclude_recent_digest_days: int,
        normalize_limit: int,
        rank_limit: int,
        topic_limit: int,
        summarize_limit: int,
        min_score: float,
    ) -> list[JobRunDTO]:
        self._require_admin(actor)
        effective_digest_date = digest_date or default_digest_date()
        return [
            self._repository.create_job(
                job_type="collect",
                trigger_type="manual",
                source_id=None,
                parent_job_run_id=None,
                created_by=actor.id,
                params={"source_types": source_types},
            ),
            self._repository.create_job(
                job_type="normalize",
                trigger_type="manual",
                source_id=None,
                parent_job_run_id=None,
                created_by=actor.id,
                params={"limit": normalize_limit},
            ),
            self._repository.create_job(
                job_type="rank",
                trigger_type="manual",
                source_id=None,
                parent_job_run_id=None,
                created_by=actor.id,
                params={"limit": rank_limit},
            ),
            self._repository.create_job(
                job_type="dedupe",
                trigger_type="manual",
                source_id=None,
                parent_job_run_id=None,
                created_by=actor.id,
                params={"limit": topic_limit},
            ),
            self._repository.create_job(
                job_type="summarize",
                trigger_type="manual",
                source_id=None,
                parent_job_run_id=None,
                created_by=actor.id,
                params={"limit": summarize_limit, "min_score": min_score},
            ),
            self._repository.create_job(
                job_type="generate_digest",
                trigger_type="manual",
                source_id=None,
                parent_job_run_id=None,
                created_by=actor.id,
                params={
                    "digest_date": effective_digest_date.isoformat(),
                    "exclude_recent_digest_days": max(exclude_recent_digest_days, 0),
                },
            ),
        ]

    def trigger_normalize(
        self,
        *,
        actor: UserDTO,
        source_id: UUID | None,
        limit: int,
        language: str | None,
    ) -> JobRunDTO:
        self._require_admin(actor)
        params: dict[str, Any] = {"limit": limit}
        if source_id is not None:
            params["source_id"] = str(source_id)
        if language is not None:
            params["language"] = language
        return self._repository.create_job(
            job_type="normalize",
            trigger_type="manual",
            source_id=source_id,
            parent_job_run_id=None,
            created_by=actor.id,
            params=params,
        )

    def trigger_rank(
        self,
        *,
        actor: UserDTO,
        source_id: UUID | None,
        limit: int,
    ) -> JobRunDTO:
        self._require_admin(actor)
        params: dict[str, Any] = {"limit": limit}
        if source_id is not None:
            params["source_id"] = str(source_id)
        return self._repository.create_job(
            job_type="rank",
            trigger_type="manual",
            source_id=source_id,
            parent_job_run_id=None,
            created_by=actor.id,
            params=params,
        )

    def trigger_topic_aggregation(
        self,
        *,
        actor: UserDTO,
        source_id: UUID | None,
        limit: int,
    ) -> JobRunDTO:
        self._require_admin(actor)
        params: dict[str, Any] = {"limit": limit}
        if source_id is not None:
            params["source_id"] = str(source_id)
        return self._repository.create_job(
            job_type="dedupe",
            trigger_type="manual",
            source_id=source_id,
            parent_job_run_id=None,
            created_by=actor.id,
            params=params,
        )

    def trigger_summarize(
        self,
        *,
        actor: UserDTO,
        source_id: UUID | None,
        limit: int,
        min_score: float,
    ) -> JobRunDTO:
        self._require_admin(actor)
        params: dict[str, Any] = {"limit": limit, "min_score": min_score}
        if source_id is not None:
            params["source_id"] = str(source_id)
        return self._repository.create_job(
            job_type="summarize",
            trigger_type="manual",
            source_id=source_id,
            parent_job_run_id=None,
            created_by=actor.id,
            params=params,
        )

    def list_scheduler_configs(
        self,
        *,
        actor: UserDTO,
        job_type: str | None,
        enabled: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SchedulerConfigDTO], int]:
        self._require_admin(actor)
        return self._repository.list_scheduler_configs(
            job_type=job_type,
            enabled=enabled,
            page=page,
            page_size=page_size,
        )

    def update_scheduler_config(
        self,
        *,
        actor: UserDTO,
        config_id: UUID,
        name: str | None,
        cron_expression: str | None,
        timezone: str | None,
        enabled: bool | None,
        params: dict[str, Any] | None,
    ) -> SchedulerConfigDTO:
        self._require_admin(actor)
        if cron_expression is not None:
            self._validate_cron_expression(cron_expression)
        if timezone is not None:
            self._validate_timezone(timezone)

        config = self._repository.update_scheduler_config(
            config_id=config_id,
            name=name.strip() if name is not None else None,
            cron_expression=cron_expression,
            timezone=timezone,
            enabled=enabled,
            params=params,
            actor_id=actor.id,
        )
        if config is None:
            raise SchedulerConfigNotFound("scheduler config not found")
        return config

    def ensure_default_scheduler_configs(self) -> list[SchedulerConfigDTO]:
        return [
            self._repository.ensure_scheduler_config(
                job_type="generate_digest",
                name="Daily AI Digest",
                cron_expression="0 8 * * *",
                timezone="Asia/Shanghai",
                enabled=True,
                params={},
            )
        ]

    def _validate_cron_expression(self, cron_expression: str) -> None:
        try:
            CronTrigger.from_crontab(cron_expression)
        except ValueError as exc:
            raise InvalidCronExpression("invalid cron expression") from exc

    def _validate_timezone(self, timezone: str) -> None:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise InvalidTimezone("invalid timezone") from exc

    def _require_admin(self, actor: UserDTO) -> None:
        if actor.role != "admin":
            raise PermissionDenied("admin role required")


def default_digest_date(now: datetime | None = None) -> date:
    base = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    return datetime.combine(base.date(), time.min, tzinfo=base.tzinfo).date()
