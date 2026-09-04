from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.identity.dtos import UserDTO
from app.application.job_operations.service import JobOperationsService
from app.domain.job_operations.exceptions import JobRunNotFound
from app.interfaces.http.dependencies import get_job_operations_service, require_admin
from app.interfaces.http.schemas import (
    JobRunResponse,
    PaginatedJobRunsResponse,
    TriggerCollectRequest,
    TriggerDailyPipelineRequest,
    TriggerGenerateDigestRequest,
    TriggerNormalizeRequest,
    TriggerRankRequest,
    TriggerSummarizeRequest,
    TriggerTopicAggregationRequest,
)

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])

JOB_TYPE_PATTERN = r"^(collect|normalize|dedupe|rank|summarize|generate_digest|publish_digest)$"
JOB_STATUS_PATTERN = r"^(pending|running|success|failed|partial_success|cancelled)$"
SOURCE_TYPE_PATTERN = r"^(rss|hacker_news|github|arxiv|product_hunt|hugging_face)$"
VALID_SOURCE_TYPES = {"rss", "hacker_news", "github", "arxiv", "product_hunt", "hugging_face"}


@router.get("")
def list_jobs(
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
    job_type: Annotated[str | None, Query(pattern=JOB_TYPE_PATTERN)] = None,
    status_filter: Annotated[str | None, Query(alias="status", pattern=JOB_STATUS_PATTERN)] = None,
    source_id: UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedJobRunsResponse:
    jobs, total = service.list_jobs(
        actor=actor,
        job_type=job_type,
        status=status_filter,
        source_id=source_id,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedJobRunsResponse(
        data=[JobRunResponse.model_validate(job) for job in jobs],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{job_run_id}")
def get_job(
    job_run_id: UUID,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    try:
        job = service.get_job(actor=actor, job_run_id=job_run_id)
    except JobRunNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found") from exc
    return {"data": JobRunResponse.model_validate(job)}


@router.post("/{job_run_id}/retry", status_code=status.HTTP_201_CREATED)
def retry_job(
    job_run_id: UUID,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    try:
        job = service.retry_job(actor=actor, job_run_id=job_run_id)
    except JobRunNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found") from exc
    return {"data": JobRunResponse.model_validate(job)}


@router.post("/collect", status_code=status.HTTP_201_CREATED)
def trigger_collect(
    payload: TriggerCollectRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    _validate_source_types(payload.source_types)
    job = service.trigger_collect(
        actor=actor,
        source_types=payload.source_types,
        since=payload.since,
        source_id=payload.source_id,
    )
    return {"data": JobRunResponse.model_validate(job)}


@router.post("/daily-pipeline", status_code=status.HTTP_201_CREATED)
def trigger_daily_pipeline(
    payload: TriggerDailyPipelineRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    _validate_source_types(payload.source_types)
    jobs = service.trigger_daily_pipeline(
        actor=actor,
        source_types=payload.source_types,
        digest_date=payload.digest_date,
        exclude_recent_digest_days=payload.exclude_recent_digest_days,
        normalize_limit=payload.normalize_limit,
        rank_limit=payload.rank_limit,
        topic_limit=payload.topic_limit,
        summarize_limit=payload.summarize_limit,
        min_score=payload.min_score,
    )
    return {"data": [JobRunResponse.model_validate(job) for job in jobs]}


@router.post("/generate-digest", status_code=status.HTTP_201_CREATED)
def trigger_generate_digest(
    payload: TriggerGenerateDigestRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    job = service.trigger_generate_digest(
        actor=actor,
        digest_date=payload.digest_date,
        exclude_recent_digest_days=payload.exclude_recent_digest_days,
    )
    return {"data": JobRunResponse.model_validate(job)}


def _validate_source_types(source_types: list[str]) -> None:
    invalid_source_types = [
        source_type for source_type in source_types if source_type not in VALID_SOURCE_TYPES
    ]
    if invalid_source_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid source type",
        )


@router.post("/normalize", status_code=status.HTTP_201_CREATED)
def trigger_normalize(
    payload: TriggerNormalizeRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    job = service.trigger_normalize(
        actor=actor,
        source_id=payload.source_id,
        limit=payload.limit,
        language=payload.language,
    )
    return {"data": JobRunResponse.model_validate(job)}


@router.post("/rank", status_code=status.HTTP_201_CREATED)
def trigger_rank(
    payload: TriggerRankRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    job = service.trigger_rank(
        actor=actor,
        source_id=payload.source_id,
        limit=payload.limit,
    )
    return {"data": JobRunResponse.model_validate(job)}


@router.post("/dedupe", status_code=status.HTTP_201_CREATED)
def trigger_topic_aggregation(
    payload: TriggerTopicAggregationRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    job = service.trigger_topic_aggregation(
        actor=actor,
        source_id=payload.source_id,
        limit=payload.limit,
    )
    return {"data": JobRunResponse.model_validate(job)}


@router.post("/summarize", status_code=status.HTTP_201_CREATED)
def trigger_summarize(
    payload: TriggerSummarizeRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[JobOperationsService, Depends(get_job_operations_service)],
) -> dict[str, object]:
    job = service.trigger_summarize(
        actor=actor,
        source_id=payload.source_id,
        limit=payload.limit,
        min_score=payload.min_score,
    )
    return {"data": JobRunResponse.model_validate(job)}
