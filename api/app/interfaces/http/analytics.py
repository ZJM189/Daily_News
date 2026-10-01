from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.application.analytics.dtos import VisitStatsDTO
from app.application.analytics.service import VisitAnalyticsService
from app.interfaces.http.dependencies import get_visit_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


class RecordVisitRequest(BaseModel):
    visitor_id: UUID
    path: str = Field(default="/", min_length=1, max_length=255)


@router.get("/visits")
async def get_visit_stats(
    service: Annotated[VisitAnalyticsService, Depends(get_visit_analytics_service)],
) -> dict[str, object]:
    return {"data": _stats_to_response(service.get_visit_stats())}


@router.post("/visits")
async def record_visit(
    payload: RecordVisitRequest,
    request: Request,
    service: Annotated[VisitAnalyticsService, Depends(get_visit_analytics_service)],
) -> dict[str, object]:
    stats = service.record_visit(
        visitor_id=str(payload.visitor_id),
        path=payload.path,
        referrer=_header_value(request.headers.get("referer"), max_length=2048),
        user_agent=_header_value(request.headers.get("user-agent"), max_length=512),
    )
    return {"data": _stats_to_response(stats)}


def _stats_to_response(stats: VisitStatsDTO) -> dict[str, int]:
    return {
        "total_visits": stats.total_visits,
        "today_visits": stats.today_visits,
        "unique_visitors": stats.unique_visitors,
        "today_unique_visitors": stats.today_unique_visitors,
    }


def _header_value(value: str | None, *, max_length: int) -> str | None:
    if not value:
        return None
    return value[:max_length]
