from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.content_library.dtos import LibrarySearchQuery
from app.application.content_library.service import ContentLibraryService
from app.application.identity.dtos import UserDTO
from app.interfaces.http.dependencies import get_content_library_service, get_current_user
from app.interfaces.http.schemas import LibraryItemResponse, PaginatedLibraryItemsResponse

router = APIRouter(prefix="/library/items", tags=["library"])

CATEGORY_PATTERN = (
    r"^(model_company|open_source|research_paper|product_launch|community|"
    r"industry_funding|other)$"
)
SOURCE_TYPE_PATTERN = r"^(rss|hacker_news|github|arxiv|product_hunt|hugging_face)$"
ITEM_STATUS_PATTERN = r"^(collected|normalized|deduped|ranked|summarized|selected|failed)$"
SORT_PATTERN = r"^(latest|score|collected)$"


@router.get("")
def search_items(
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


@router.get("/{item_id}")
def get_item(
    item_id: UUID,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryService, Depends(get_content_library_service)],
) -> dict[str, object]:
    item = service.get_item(actor=actor, item_id=item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="item not found")
    return {"data": LibraryItemResponse.model_validate(item)}
