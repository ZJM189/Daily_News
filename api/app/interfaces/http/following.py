from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.identity.dtos import UserDTO
from app.application.personalization.dtos import UserPreferenceDTO
from app.application.personalization.service import PersonalizationService
from app.interfaces.http.dependencies import get_current_user, get_personalization_service
from app.interfaces.http.schemas import (
    CreateFeedbackRequest,
    CreateSavedSearchRequest,
    FollowingItemResponse,
    PaginatedFollowingItemsResponse,
    SavedSearchResponse,
    UpdateSavedSearchRequest,
    UpdateUserPreferenceRequest,
    UserPreferenceResponse,
)

router = APIRouter(prefix="/following", tags=["following"])


@router.get("/preferences")
async def get_preferences(
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
) -> dict[str, object]:
    preference = service.get_preference(actor=actor)
    return {"data": UserPreferenceResponse.model_validate(preference)}


@router.put("/preferences")
async def update_preferences(
    payload: UpdateUserPreferenceRequest,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
) -> dict[str, object]:
    preference = service.save_preference(
        actor=actor,
        preference=UserPreferenceDTO(
            follow_keywords=payload.follow_keywords,
            exclude_keywords=payload.exclude_keywords,
            follow_categories=payload.follow_categories,
            follow_source_types=payload.follow_source_types,
            disabled_source_types=payload.disabled_source_types,
            blocked_source_ids=[str(source_id) for source_id in payload.blocked_source_ids],
            blocked_domains=payload.blocked_domains,
            weights=payload.weights,
        ),
    )
    return {"data": UserPreferenceResponse.model_validate(preference)}


@router.get("/items")
async def list_following_items(
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedFollowingItemsResponse:
    items, total = service.list_following_items(actor=actor, page=page, page_size=page_size)
    return PaginatedFollowingItemsResponse(
        data=[FollowingItemResponse.model_validate(item) for item in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/saved-searches")
async def list_saved_searches(
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
) -> dict[str, object]:
    searches = service.list_saved_searches(actor=actor)
    return {"data": [SavedSearchResponse.model_validate(search) for search in searches]}


@router.post("/saved-searches")
async def create_saved_search(
    payload: CreateSavedSearchRequest,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
) -> dict[str, object]:
    search = service.create_saved_search(
        actor=actor,
        name=payload.name,
        query=payload.query,
        apply_as_filter=payload.apply_as_filter,
        apply_as_boost=payload.apply_as_boost,
        enabled=payload.enabled,
    )
    return {"data": SavedSearchResponse.model_validate(search)}


@router.patch("/saved-searches/{search_id}")
async def update_saved_search(
    search_id: UUID,
    payload: UpdateSavedSearchRequest,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
) -> dict[str, object]:
    try:
        search = service.update_saved_search(
            actor=actor,
            search_id=search_id,
            name=payload.name,
            query=payload.query,
            apply_as_filter=payload.apply_as_filter,
            apply_as_boost=payload.apply_as_boost,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"data": SavedSearchResponse.model_validate(search)}


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: UUID,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
) -> dict[str, object]:
    try:
        service.delete_saved_search(actor=actor, search_id=search_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"data": {"ok": True}}


@router.post("/feedback")
async def create_feedback(
    payload: CreateFeedbackRequest,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[PersonalizationService, Depends(get_personalization_service)],
) -> dict[str, object]:
    try:
        service.record_feedback(
            actor=actor,
            action=payload.action,
            item_id=payload.item_id,
            source_id=payload.source_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"data": {"status": "ok"}}
