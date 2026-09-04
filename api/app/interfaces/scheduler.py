from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.job_operations.dtos import SchedulerConfigDTO
from app.infrastructure.config import get_settings
from app.infrastructure.job_operations.repositories import SqlAlchemyJobOperationsRepository
from app.infrastructure.models import JobType
from app.infrastructure.persistence import get_session_factory

logger = logging.getLogger("daily_news.scheduler")
SCHEDULE_JOB_PREFIX = "scheduler-config:"
REFRESH_JOB_ID = "scheduler-refresh"
REFRESH_INTERVAL_SECONDS = 60


@dataclass(frozen=True, slots=True)
class ScheduledJobDefinition:
    job_type: str
    params: dict[str, Any]
    source_id: UUID | None = None


def _config_job_id(config_id: UUID) -> str:
    return f"{SCHEDULE_JOB_PREFIX}{config_id}"


def _load_enabled_configs() -> list[SchedulerConfigDTO]:
    session = get_session_factory()()
    try:
        repository = SqlAlchemyJobOperationsRepository(session)
        configs, _ = repository.list_scheduler_configs(
            job_type=None,
            enabled=True,
            page=1,
            page_size=100,
        )
        return configs
    finally:
        session.close()


def _build_trigger(config: SchedulerConfigDTO) -> CronTrigger:
    try:
        timezone = ZoneInfo(config.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"invalid scheduler timezone: {config.timezone}") from exc
    try:
        return CronTrigger.from_crontab(config.cron_expression, timezone=timezone)
    except ValueError as exc:
        raise ValueError(
            f"invalid scheduler cron expression: {config.cron_expression}"
        ) from exc


def _refresh_schedules(scheduler: BackgroundScheduler) -> None:
    try:
        configs = _load_enabled_configs()
    except Exception:
        logger.exception("failed to load scheduler configs")
        return

    active_job_ids: set[str] = set()
    for config in configs:
        job_id = _config_job_id(config.id)
        try:
            trigger = _build_trigger(config)
        except ValueError:
            logger.exception("skipped invalid scheduler config %s", config.id)
            continue

        existing_job = scheduler.get_job(job_id)
        if existing_job is None or str(existing_job.trigger) != str(trigger):
            scheduler.add_job(
                _enqueue_scheduled_job,
                trigger=trigger,
                args=[config.id],
                id=job_id,
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=3600,
            )
        active_job_ids.add(job_id)

    for job in scheduler.get_jobs():
        if job.id.startswith(SCHEDULE_JOB_PREFIX) and job.id not in active_job_ids:
            scheduler.remove_job(job.id)

    logger.info("scheduler configs loaded: %s active", len(active_job_ids))


def _scheduled_job_params(
    config: SchedulerConfigDTO,
    now: datetime | None = None,
) -> dict[str, Any]:
    params = dict(config.params or {})
    if config.job_type != JobType.GENERATE_DIGEST.value:
        return params

    current_time = _now_in_timezone(config.timezone, now=now)
    digest_params = {
        "digest_date": params.get("digest_date", current_time.date().isoformat()),
        "timezone": params.get("timezone", config.timezone),
        "limit": _positive_int(params.get("limit"), default=20, maximum=100),
        "exclude_recent_digest_days": _non_negative_int(
            params.get("exclude_recent_digest_days"),
            default=3,
            maximum=30,
        ),
    }
    return digest_params


def _scheduled_job_definitions(
    config: SchedulerConfigDTO,
    now: datetime | None = None,
) -> list[ScheduledJobDefinition]:
    params = dict(config.params or {})
    if config.job_type != JobType.GENERATE_DIGEST.value:
        return [
            ScheduledJobDefinition(
                job_type=config.job_type,
                params=params,
            )
        ]

    digest_params = _scheduled_job_params(config, now=now)
    collect_params: dict[str, Any] = {
        "source_types": _string_list(params.get("source_types")),
    }
    if isinstance(params.get("since"), str):
        collect_params["since"] = params["since"]

    normalize_params: dict[str, Any] = {
        "limit": _positive_int(params.get("normalize_limit"), default=5000, maximum=5000),
    }
    if isinstance(params.get("language"), str):
        normalize_params["language"] = params["language"]

    return [
        ScheduledJobDefinition(job_type=JobType.COLLECT.value, params=collect_params),
        ScheduledJobDefinition(job_type=JobType.NORMALIZE.value, params=normalize_params),
        ScheduledJobDefinition(
            job_type=JobType.RANK.value,
            params={"limit": _positive_int(params.get("rank_limit"), default=5000, maximum=5000)},
        ),
        ScheduledJobDefinition(
            job_type=JobType.DEDUPE.value,
            params={"limit": _positive_int(params.get("topic_limit"), default=1000, maximum=5000)},
        ),
        ScheduledJobDefinition(
            job_type=JobType.SUMMARIZE.value,
            params={
                "limit": _positive_int(
                    params.get("summarize_limit"),
                    default=100,
                    maximum=1000,
                ),
                "min_score": _float_param(params.get("min_score"), default=60.0),
            },
        ),
        ScheduledJobDefinition(job_type=JobType.GENERATE_DIGEST.value, params=digest_params),
    ]


def _enqueue_scheduled_job(config_id: UUID) -> None:
    session = get_session_factory()()
    try:
        repository = SqlAlchemyJobOperationsRepository(session)
        config = repository.get_scheduler_config(config_id)
        if config is None or not config.enabled:
            logger.info("scheduler config %s is disabled or missing", config_id)
            return

        created_jobs = []
        for job_definition in _scheduled_job_definitions(config):
            created_jobs.append(
                repository.create_job(
                    job_type=job_definition.job_type,
                    trigger_type="scheduled",
                    source_id=job_definition.source_id,
                    parent_job_run_id=None,
                    created_by=None,
                    params=job_definition.params,
                )
            )
        session.commit()
        logger.info(
            "scheduled jobs created: config=%s count=%s types=%s",
            config_id,
            len(created_jobs),
            ",".join(job.job_type for job in created_jobs),
        )
    except Exception:
        session.rollback()
        logger.exception("failed to create scheduled job for config %s", config_id)
    finally:
        session.close()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _positive_int(value: object, *, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < 1:
        return default
    return min(number, maximum)


def _float_param(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _non_negative_int(value: object, *, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < 0:
        return default
    return min(number, maximum)


def _now_in_timezone(timezone: str, *, now: datetime | None = None) -> datetime:
    tzinfo = ZoneInfo(timezone)
    if now is None:
        return datetime.now(tzinfo)
    if now.tzinfo is None:
        return now.replace(tzinfo=tzinfo)
    return now.astimezone(tzinfo)


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    session = get_session_factory()()
    try:
        repository = SqlAlchemyJobOperationsRepository(session)
        repository.ensure_scheduler_config(
            job_type=JobType.GENERATE_DIGEST.value,
            name="Daily AI Digest",
            cron_expression=settings.digest_cron,
            timezone=settings.default_timezone,
            enabled=True,
            params={},
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    scheduler = BackgroundScheduler(timezone=settings.default_timezone)
    scheduler.add_job(
        _refresh_schedules,
        trigger="interval",
        seconds=REFRESH_INTERVAL_SECONDS,
        args=[scheduler],
        id=REFRESH_JOB_ID,
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _refresh_schedules(scheduler)
    scheduler.start()
    logger.info("scheduler started")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("scheduler stopping")
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
