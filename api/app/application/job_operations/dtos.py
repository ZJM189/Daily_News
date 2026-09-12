from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class JobRunDTO:
    id: UUID
    job_type: str
    trigger_type: str
    status: str
    source_id: UUID | None
    parent_job_run_id: UUID | None
    created_by: UUID | None
    params: dict[str, Any]
    total_count: int
    success_count: int
    duplicate_count: int
    failure_count: int
    error_message: str | None
    error_detail: dict[str, Any] | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SchedulerConfigDTO:
    id: UUID
    job_type: str
    name: str
    cron_expression: str
    timezone: str
    enabled: bool
    params: dict[str, Any]
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime
