from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.application.identity.dtos import UserDTO
from app.application.identity.service import IdentityService
from app.application.identity.tokens import hash_ip_address
from app.domain.identity.exceptions import AuthenticationFailed, UserDisabled
from app.infrastructure.config import Settings, get_settings
from app.interfaces.http.dependencies import (
    get_current_user,
    get_identity_service,
    get_session_token,
)
from app.interfaces.http.schemas import LoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    try:
        session = identity_service.login(
            login=payload.login,
            password=payload.password,
            ip_hash=hash_ip_address(
                request.client.host if request.client else None,
                settings.session_secret,
            ),
            user_agent=request.headers.get("user-agent"),
        )
    except AuthenticationFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid login or password",
        ) from exc
    except UserDisabled as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user disabled") from exc

    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.session_cookie_samesite,
        expires=session.expires_at,
    )
    return {"data": {"user": UserResponse.model_validate(session.user)}}


@router.post("/logout")
def logout(
    response: Response,
    token: Annotated[str | None, Depends(get_session_token)],
    _current_user: Annotated[UserDTO, Depends(get_current_user)],
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    if token:
        identity_service.logout(token)
    response.delete_cookie(
        key=settings.session_cookie_name,
        secure=settings.cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return {"data": {"ok": True}}


@router.get("/me")
def me(current_user: Annotated[UserDTO, Depends(get_current_user)]) -> dict[str, object]:
    return {"data": UserResponse.model_validate(current_user)}
