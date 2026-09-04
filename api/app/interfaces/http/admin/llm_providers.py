from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.identity.dtos import UserDTO
from app.application.llm_operations.service import LLMProviderService
from app.domain.llm_operations.exceptions import LLMProviderAlreadyExists, LLMProviderNotFound
from app.interfaces.http.dependencies import get_llm_provider_service, require_admin
from app.interfaces.http.schemas import (
    CreateLLMProviderRequest,
    LLMProviderResponse,
    PaginatedLLMProvidersResponse,
    UpdateLLMProviderRequest,
)

router = APIRouter(prefix="/admin/llm-providers", tags=["admin-llm-providers"])


@router.get("")
def list_llm_providers(
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[LLMProviderService, Depends(get_llm_provider_service)],
    enabled: bool | None = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedLLMProvidersResponse:
    providers, total = service.list_providers(
        actor=actor,
        enabled=enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PaginatedLLMProvidersResponse(
        data=[LLMProviderResponse.model_validate(provider) for provider in providers],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_llm_provider(
    payload: CreateLLMProviderRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[LLMProviderService, Depends(get_llm_provider_service)],
) -> dict[str, object]:
    try:
        provider = service.create_provider(
            actor=actor,
            name=payload.name,
            base_url=payload.base_url,
            model=payload.model,
            api_key=payload.api_key,
            timeout_seconds=payload.timeout_seconds,
            retry_count=payload.retry_count,
            enabled=payload.enabled,
            is_default=payload.is_default,
        )
    except LLMProviderAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="llm provider exists",
        ) from exc
    return {"data": LLMProviderResponse.model_validate(provider)}


@router.patch("/{provider_id}")
def update_llm_provider(
    provider_id: UUID,
    payload: UpdateLLMProviderRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[LLMProviderService, Depends(get_llm_provider_service)],
) -> dict[str, object]:
    try:
        provider = service.update_provider(
            actor=actor,
            provider_id=provider_id,
            name=payload.name,
            base_url=payload.base_url,
            model=payload.model,
            api_key=payload.api_key,
            api_key_provided="api_key" in payload.model_fields_set,
            timeout_seconds=payload.timeout_seconds,
            retry_count=payload.retry_count,
            enabled=payload.enabled,
            is_default=payload.is_default,
        )
    except LLMProviderNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="llm provider not found",
        ) from exc
    except LLMProviderAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="llm provider exists",
        ) from exc
    return {"data": LLMProviderResponse.model_validate(provider)}


@router.post("/{provider_id}/set-default")
def set_default_llm_provider(
    provider_id: UUID,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[LLMProviderService, Depends(get_llm_provider_service)],
) -> dict[str, object]:
    try:
        provider = service.set_default_provider(actor=actor, provider_id=provider_id)
    except LLMProviderNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="llm provider not found",
        ) from exc
    return {"data": LLMProviderResponse.model_validate(provider)}
