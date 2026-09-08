from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.content_library.dtos import LibraryAnalyticsQuery, LibrarySearchQuery
from app.application.content_library.service import ContentLibraryService
from app.application.identity.dtos import UserDTO
from app.interfaces.http.dependencies import get_content_library_service, get_current_user
from app.interfaces.http.schemas import (
    LibraryAnalyticsResponse,
    LibraryItemResponse,
    NaturalLanguageLibrarySearchRequest,
    NaturalLanguageLibrarySearchResponse,
    PaginatedLibraryItemsResponse,
)

router = APIRouter(prefix="/library", tags=["library"])

CATEGORY_PATTERN = (
    r"^(model_company|open_source|research_paper|product_launch|community|"
    r"industry_funding|other)$"
)
SOURCE_TYPE_PATTERN = r"^(rss|hacker_news|github|arxiv|product_hunt|hugging_face)$"
ITEM_STATUS_PATTERN = r"^(collected|normalized|deduped|ranked|summarized|selected|failed)$"
SORT_PATTERN = r"^(latest|score|collected)$"


@router.post("/natural-language-search")
async def natural_language_search(
    request: NaturalLanguageLibrarySearchRequest,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
) -> NaturalLanguageLibrarySearchResponse:
    result = service.natural_language_search(
        actor=actor,
        query=request.query,
        page_size=request.page_size,
    )
    interpreted_query = result.interpreted_query
    return NaturalLanguageLibrarySearchResponse(
        mode=result.mode,
        explanation=result.explanation,
        interpreted_query={
            "keyword": interpreted_query.keyword,
            "search_terms": list(interpreted_query.search_terms),
            "category": interpreted_query.category,
            "source_type": interpreted_query.source_type,
            "source_id": interpreted_query.source_id,
            "status": interpreted_query.status,
            "published_from": interpreted_query.published_from,
            "published_to": interpreted_query.published_to,
            "min_score": interpreted_query.min_score,
            "has_summary": interpreted_query.has_summary,
            "sort": interpreted_query.sort,
            "page_size": interpreted_query.page_size,
        },
        chips=[{"key": chip.key, "label": chip.label} for chip in result.chips],
        data=[LibraryItemResponse.model_validate(item) for item in result.items],
        meta={"page": result.page, "page_size": result.page_size, "total": result.total},
        library_url=result.library_url,
        llm=(
            {
                "provider": result.llm.provider,
                "model": result.llm.model,
                "confidence": result.llm.confidence,
            }
            if result.llm
            else None
        ),
    )


@router.get("/items")
async def search_items(
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(pattern=CATEGORY_PATTERN)] = None,
    source_type: Annotated[str | None, Query(pattern=SOURCE_TYPE_PATTERN)] = None,
    source_id: UUID | None = None,
    item_status: Annotated[str | None, Query(alias="status", pattern=ITEM_STATUS_PATTERN)] = None,
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    has_summary: bool | None = None,
    sort: Annotated[str, Query(pattern=SORT_PATTERN)] = "latest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedLibraryItemsResponse:
    items, total = service.search_items(
        actor=actor,
        query=LibrarySearchQuery(
            keyword=keyword,
            category=category,
            source_type=source_type,
            source_id=source_id,
            status=item_status,
            published_from=published_from,
            published_to=published_to,
            min_score=min_score,
            has_summary=has_summary,
            sort=sort,
        ),
        page=page,
        page_size=page_size,
    )
    return PaginatedLibraryItemsResponse(
        data=[LibraryItemResponse.model_validate(item) for item in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/analytics")
async def get_library_analytics(
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(pattern=CATEGORY_PATTERN)] = None,
    source_type: Annotated[str | None, Query(pattern=SOURCE_TYPE_PATTERN)] = None,
    source_id: UUID | None = None,
    item_status: Annotated[str | None, Query(alias="status", pattern=ITEM_STATUS_PATTERN)] = None,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    has_summary: bool | None = None,
    window_days: Annotated[int, Query(ge=0, le=365)] = 30,
) -> dict[str, LibraryAnalyticsResponse]:
    analytics = service.get_analytics(
        actor=actor,
        query=LibraryAnalyticsQuery(
            keyword=keyword,
            category=category,
            source_type=source_type,
            source_id=source_id,
            status=item_status,
            min_score=min_score,
            has_summary=has_summary,
            window_days=window_days,
        ),
    )
    return {"data": LibraryAnalyticsResponse.model_validate(analytics)}


@router.get("/items/{item_id}")
async def get_item(
    item_id: UUID,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
) -> dict[str, object]:
    item = service.get_item(actor=actor, item_id=item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="item not found")
    return {"data": LibraryItemResponse.model_validate(item)}
