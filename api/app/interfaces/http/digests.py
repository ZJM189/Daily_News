from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from app.application.digest_publishing.dtos import DigestDetailDTO, DigestItemDTO
from app.application.digest_publishing.service import DigestQueryService
from app.application.identity.dtos import UserDTO
from app.interfaces.http.dependencies import get_current_user, get_digest_query_service
from app.interfaces.http.schemas import DigestItemResponse, DigestResponse

router = APIRouter(prefix="/digests", tags=["digests"])


@router.get("/today")
async def get_today_digest(
    service: Annotated[DigestQueryService, Depends(get_digest_query_service)],
    view: Annotated[str, Query(pattern=r"^(system|following)$")] = "system",
) -> dict[str, object]:
    digest_date = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    detail = service.get_published_digest(digest_date=digest_date, version=None)
    return {"data": _detail_to_response(detail)}


@router.get("/{digest_date}")
async def get_digest(
    digest_date: date,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[DigestQueryService, Depends(get_digest_query_service)],
    version: Annotated[int | None, Query(ge=1)] = None,
    view: Annotated[str, Query(pattern=r"^(system|following)$")] = "system",
) -> dict[str, object]:
    detail = service.get_published_digest(digest_date=digest_date, version=version)
    return {"data": _detail_to_response(detail)}


def _detail_to_response(detail: DigestDetailDTO | None) -> DigestResponse | None:
    if detail is None:
        return None
    digest = detail.digest
    return DigestResponse(
        id=digest.id,
        digest_date=digest.digest_date,
        version=digest.version,
        status=digest.status,
        title=digest.title,
        overview_zh=digest.overview_zh,
        stats=digest.stats,
        job_run_id=digest.job_run_id,
        generated_at=digest.generated_at,
        published_at=digest.published_at,
        created_at=digest.created_at,
        items=[_item_to_response(item) for item in detail.items],
    )


def _item_to_response(item: DigestItemDTO) -> DigestItemResponse:
    return DigestItemResponse(
        id=item.id,
        item_id=item.item_id,
        topic_id=item.topic_id,
        item_type=item.item_type,
        rank=item.rank,
        score_snapshot=float(item.score_snapshot),
        title_snapshot=item.title_snapshot,
        summary_snapshot_zh=item.summary_snapshot_zh,
        importance_snapshot_zh=item.importance_snapshot_zh,
        category_snapshot=item.category_snapshot,
        source_snapshot=item.source_snapshot,
        created_at=item.created_at,
    )
