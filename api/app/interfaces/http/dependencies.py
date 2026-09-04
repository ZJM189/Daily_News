from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.content_library.service import ContentLibraryService
from app.application.digest_publishing.service import DigestQueryService
from app.application.identity.dtos import UserDTO
from app.application.identity.passwords import PasswordService
from app.application.identity.service import IdentityService
from app.application.job_operations.service import JobOperationsService
from app.application.llm_operations.service import LLMProviderService
from app.application.personalization.service import PersonalizationService
from app.application.source_management.service import SourceManagementService
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.content_library.factory import create_content_library_service
from app.infrastructure.digest_publishing.factory import create_digest_query_service
from app.infrastructure.identity.repositories import SqlAlchemyIdentityRepository
from app.infrastructure.job_operations.repositories import SqlAlchemyJobOperationsRepository
from app.infrastructure.llm_operations.repositories import SqlAlchemyLLMProviderRepository
from app.infrastructure.persistence import iter_session
from app.infrastructure.personalization.factory import create_personalization_service
from app.infrastructure.secrets import SecretCipher
from app.infrastructure.source_management.repositories import SqlAlchemySourceManagementRepository


def get_db_session() -> Iterator[Session]:
    yield from iter_session()


def get_identity_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IdentityService:
    return IdentityService(
        SqlAlchemyIdentityRepository(session),
        PasswordService(),
        session_ttl_hours=settings.session_ttl_hours,
    )


def get_source_management_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SourceManagementService:
    return SourceManagementService(
        SqlAlchemySourceManagementRepository(session),
        SecretCipher(settings.encryption_key),
    )


def get_llm_provider_service(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LLMProviderService:
    return LLMProviderService(
        SqlAlchemyLLMProviderRepository(session),
        SecretCipher(settings.encryption_key),
    )


def get_job_operations_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> JobOperationsService:
    return JobOperationsService(SqlAlchemyJobOperationsRepository(session))


def get_digest_query_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> DigestQueryService:
    return create_digest_query_service(session)


def get_content_library_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> ContentLibraryService:
    return create_content_library_service(session)


def get_personalization_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> PersonalizationService:
    return create_personalization_service(session)


def get_session_token(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def get_current_user(
    token: Annotated[str | None, Depends(get_session_token)],
    identity_service: Annotated[IdentityService, Depends(get_identity_service)],
) -> UserDTO:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")

    user = identity_service.get_user_by_session_token(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="UNAUTHORIZED")
    return user


def require_admin(current_user: Annotated[UserDTO, Depends(get_current_user)]) -> UserDTO:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")
    return current_user
