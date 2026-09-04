from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.identity.dtos import UserDTO
from app.application.source_management.service import SourceManagementService
from app.domain.source_management.exceptions import CredentialNotFound, SourceNotFound
from app.interfaces.http.dependencies import get_source_management_service, require_admin
from app.interfaces.http.schemas import (
    CreateSourceRequest,
    PaginatedSourcesResponse,
    SourceResponse,
    UpdateSourceRequest,
)

router = APIRouter(prefix="/admin/sources", tags=["admin-sources"])


@router.get("")
def list_sources(
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[SourceManagementService, Depends(get_source_management_service)],
    source_type: Annotated[
        str | None,
        Query(alias="type", pattern=r"^(rss|hacker_news|github|arxiv|product_hunt|hugging_face)$"),
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern=r"^(enabled|disabled|missing_token|error)$"),
    ] = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedSourcesResponse:
    sources, total = service.list_sources(
        actor=actor,
        source_type=source_type,
        status=status_filter,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PaginatedSourcesResponse(
        data=[SourceResponse.model_validate(source) for source in sources],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_source(
    payload: CreateSourceRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[SourceManagementService, Depends(get_source_management_service)],
) -> dict[str, object]:
    try:
        source = service.create_source(
            actor=actor,
            name=payload.name,
            source_type=payload.type,
            status=payload.status,
            url=payload.url,
            query_config=payload.query_config,
            credential_id=payload.credential_id,
            credential_env_key=payload.credential_env_key,
            weight=payload.weight,
            language=payload.language,
        )
    except CredentialNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source credential not found",
        ) from exc
    return {"data": SourceResponse.model_validate(source)}


@router.patch("/{source_id}")
def update_source(
    source_id: UUID,
    payload: UpdateSourceRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[SourceManagementService, Depends(get_source_management_service)],
) -> dict[str, object]:
    try:
        source = service.update_source(
            actor=actor,
            source_id=source_id,
            name=payload.name,
            status=payload.status,
            url=payload.url,
            url_provided="url" in payload.model_fields_set,
            query_config=payload.query_config,
            credential_id=payload.credential_id,
            credential_id_provided="credential_id" in payload.model_fields_set,
            credential_env_key=payload.credential_env_key,
            credential_env_key_provided="credential_env_key" in payload.model_fields_set,
            weight=payload.weight,
            language=payload.language,
            language_provided="language" in payload.model_fields_set,
        )
    except SourceNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="source not found") from exc
    except CredentialNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source credential not found",
        ) from exc
    return {"data": SourceResponse.model_validate(source)}
