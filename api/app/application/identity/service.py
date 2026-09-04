from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.application.identity.dtos import SessionDTO, UserDTO
from app.application.identity.passwords import PasswordService
from app.application.identity.repositories import IdentityRepository
from app.application.identity.tokens import generate_session_token, hash_session_token
from app.domain.identity.exceptions import (
    AdminAlreadyInitialized,
    AuthenticationFailed,
    PermissionDenied,
    UserAlreadyExists,
    UserDisabled,
    UserNotFound,
)


class IdentityService:
    def __init__(
        self,
        repository: IdentityRepository,
        password_service: PasswordService,
        *,
        session_ttl_hours: int,
    ) -> None:
        self._repository = repository
        self._password_service = password_service
        self._session_ttl_hours = session_ttl_hours

    def create_first_admin(
        self,
        *,
        username: str,
        email: str | None,
        display_name: str | None,
        password: str,
    ) -> UserDTO:
        if self._repository.has_any_user():
            raise AdminAlreadyInitialized("first admin can only be created before any user exists")

        return self._create_user(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
            role="admin",
            status="active",
            created_by=None,
        )

    def create_user_by_admin(
        self,
        *,
        actor: UserDTO,
        username: str,
        email: str | None,
        display_name: str | None,
        password: str,
        role: str,
        status: str,
    ) -> UserDTO:
        self._require_admin(actor)
        return self._create_user(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
            role=role,
            status=status,
            created_by=actor.id,
        )

    def login(
        self,
        *,
        login: str,
        password: str,
        ip_hash: str | None,
        user_agent: str | None,
    ) -> SessionDTO:
        user = self._repository.get_user_by_login(login)
        if user is None:
            raise AuthenticationFailed("invalid login or password")
        if user.status == "disabled":
            raise UserDisabled("user is disabled")

        password_hash = self._get_password_hash(login)
        if not self._password_service.verify_password(password_hash, password):
            raise AuthenticationFailed("invalid login or password")

        now = datetime.now(UTC)
        token = generate_session_token()
        expires_at = now + timedelta(hours=self._session_ttl_hours)
        self._repository.create_session(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=expires_at,
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        self._repository.update_last_login(user_id=user.id, logged_in_at=now)

        refreshed_user = self._repository.get_user_by_id(user.id) or user
        return SessionDTO(token=token, expires_at=expires_at, user=refreshed_user)

    def get_user_by_session_token(self, token: str) -> UserDTO | None:
        return self._repository.get_user_by_session_token_hash(
            hash_session_token(token),
            datetime.now(UTC),
        )

    def logout(self, token: str) -> bool:
        return self._repository.revoke_session(hash_session_token(token), datetime.now(UTC))

    def list_users(
        self,
        *,
        actor: UserDTO,
        role: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[UserDTO], int]:
        self._require_admin(actor)
        return self._repository.list_users(
            role=role,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def update_user_by_admin(
        self,
        *,
        actor: UserDTO,
        user_id: UUID,
        display_name: str | None,
        role: str | None,
        status: str | None,
    ) -> UserDTO:
        self._require_admin(actor)
        user = self._repository.update_user(
            user_id=user_id,
            display_name=display_name,
            role=role,
            status=status,
        )
        if user is None:
            raise UserNotFound("user not found")
        if status == "disabled":
            self._repository.revoke_user_sessions(user_id, datetime.now(UTC))
        return user

    def reset_password_by_admin(
        self,
        *,
        actor: UserDTO,
        user_id: UUID,
        new_password: str,
    ) -> None:
        self._require_admin(actor)
        password_hash = self._password_service.hash_password(new_password)
        if not self._repository.update_password(user_id=user_id, password_hash=password_hash):
            raise UserNotFound("user not found")
        self._repository.revoke_user_sessions(user_id, datetime.now(UTC))

    def _create_user(
        self,
        *,
        username: str,
        email: str | None,
        display_name: str | None,
        password: str,
        role: str,
        status: str,
        created_by: UUID | None,
    ) -> UserDTO:
        username = username.strip()
        email = email.lower().strip() if email else None
        display_name = display_name.strip() if display_name else None
        password_hash = self._password_service.hash_password(password)
        try:
            return self._repository.create_user(
                username=username,
                email=email,
                display_name=display_name,
                password_hash=password_hash,
                role=role,
                status=status,
                created_by=created_by,
            )
        except ValueError as exc:
            raise UserAlreadyExists("username or email already exists") from exc

    def _require_admin(self, actor: UserDTO) -> None:
        if actor.role != "admin":
            raise PermissionDenied("admin role required")

    def _get_password_hash(self, login: str) -> str:
        password_hash = self._repository.get_password_hash_by_login(login)
        if password_hash is None:
            raise AuthenticationFailed("invalid login or password")
        return password_hash
