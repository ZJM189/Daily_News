from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.identity.dtos import UserDTO
from app.application.job_operations.service import JobOperationsService
from app.domain.job_operations.exceptions import (
    InvalidCronExpression,
    InvalidTimezone,
    SchedulerConfigNotFound,
)
from app.interfaces.http.dependencies import get_job_operations_service, require_admin
from app.interfaces.http.schemas import (
    PaginatedSchedulerConfigsResponse,
    SchedulerConfigResponse,
    UpdateSchedulerConfigRequest,
)

router = APIRouter(prefix="/admin/scheduler/configs", tags=["admin-scheduler"])

JOB_TYPE_PATTERN = r"^(collect|normalize|dedupe|rank|summarize|generate_digest|publish_digest)$"


@router.get("")
def list_scheduler_configs(
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
    job_type: Annotated[str | None, Query(pattern=JOB_TYPE_PATTERN)] = None,
    enabled: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedSchedulerConfigsResponse:
    configs, total = service.list_scheduler_configs(
        actor=actor,
        job_type=job_type,
        enabled=enabled,
        page=page,
        page_size=page_size,
    )
    return PaginatedSchedulerConfigsResponse(
        data=[SchedulerConfigResponse.model_validate(config) for config in configs],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.patch("/{config_id}")
def update_scheduler_config(
    config_id: UUID,
    payload: UpdateSchedulerConfigRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    try:
        config = service.update_scheduler_config(
            actor=actor,
            config_id=config_id,
            name=payload.name,
            cron_expression=payload.cron_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            params=payload.params,
        )
    except SchedulerConfigNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="scheduler config not found",
        ) from exc
    except InvalidCronExpression as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid cron expression",
        ) from exc
    except InvalidTimezone as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid timezone",
        ) from exc
    return {"data": SchedulerConfigResponse.model_validate(config)}
