from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.identity.dtos import UserDTO
from app.application.source_management.service import SourceManagementService
from app.domain.source_management.exceptions import CredentialNotFound
from app.interfaces.http.dependencies import get_source_management_service, require_admin
from app.interfaces.http.schemas import (
    CreateSourceCredentialRequest,
    PaginatedSourceCredentialsResponse,
    SourceCredentialResponse,
    UpdateSourceCredentialRequest,
)

router = APIRouter(prefix="/admin/source-credentials", tags=["admin-source-credentials"])


@router.get("")
def list_source_credentials(
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[SourceManagementService, Depends(get_source_management_service)],
    source_type: Annotated[
        str | None,
        Query(pattern=r"^(rss|hacker_news|github|arxiv|product_hunt|hugging_face)$"),
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern=r"^(active|disabled|missing|error)$"),
    ] = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedSourceCredentialsResponse:
    credentials, total = service.list_credentials(
        actor=actor,
        source_type=source_type,
        status=status_filter,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PaginatedSourceCredentialsResponse(
        data=[SourceCredentialResponse.model_validate(credential) for credential in credentials],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_source_credential(
    payload: CreateSourceCredentialRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[SourceManagementService, Depends(get_source_management_service)],
) -> dict[str, object]:
    credential = service.create_credential(
        actor=actor,
        name=payload.name,
        source_type=payload.source_type,
        secret=payload.secret,
        status=payload.status,
    )
    return {"data": SourceCredentialResponse.model_validate(credential)}


@router.patch("/{credential_id}")
def update_source_credential(
    credential_id: UUID,
    payload: UpdateSourceCredentialRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    service: Annotated[SourceManagementService, Depends(get_source_management_service)],
) -> dict[str, object]:
    try:
        credential = service.update_credential(
            actor=actor,
            credential_id=credential_id,
            name=payload.name,
            secret=payload.secret,
            secret_provided="secret" in payload.model_fields_set,
            status=payload.status,
        )
    except CredentialNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source credential not found",
        ) from exc
    return {"data": SourceCredentialResponse.model_validate(credential)}
