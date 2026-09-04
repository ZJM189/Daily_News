from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.identity.dtos import UserDTO
from app.application.identity.service import IdentityService
from app.domain.identity.exceptions import InvalidPassword, UserAlreadyExists, UserNotFound
from app.interfaces.http.dependencies import get_identity_service, require_admin
from app.interfaces.http.schemas import (
    CreateUserRequest,
    PaginatedUsersResponse,
    ResetPasswordRequest,
    UpdateUserRequest,
    UserResponse,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("")
def list_users(
    actor: Annotated[UserDTO, Depends(require_admin)],
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
    role: Annotated[str | None, Query(pattern=r"^(user|admin)$")] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", pattern=r"^(active|disabled)$"),
    ] = None,
    keyword: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedUsersResponse:
    users, total = identity_service.list_users(
        actor=actor,
        role=role,
        status=status_filter,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PaginatedUsersResponse(
        data=[UserResponse.model_validate(user) for user in users],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: CreateUserRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
) -> dict[str, object]:
    try:
        user = identity_service.create_user_by_admin(
            actor=actor,
            username=payload.username,
            email=payload.email.lower() if payload.email else None,
            display_name=payload.display_name,
            password=payload.password,
            role=payload.role,
            status=payload.status,
        )
    except UserAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user exists") from exc
    except InvalidPassword as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {"data": UserResponse.model_validate(user)}


@router.patch("/{user_id}")
def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
) -> dict[str, object]:
    try:
        user = identity_service.update_user_by_admin(
            actor=actor,
            user_id=user_id,
            display_name=payload.display_name,
            role=payload.role,
            status=payload.status,
        )
    except UserNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") from exc
    return {"data": UserResponse.model_validate(user)}


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: UUID,
    payload: ResetPasswordRequest,
    actor: Annotated[UserDTO, Depends(require_admin)],
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
) -> dict[str, object]:
    try:
        identity_service.reset_password_by_admin(
            actor=actor,
            user_id=user_id,
            new_password=payload.new_password,
        )
    except UserNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found") from exc
    except InvalidPassword as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"data": {"ok": True}}
