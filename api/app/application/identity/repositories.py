from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.identity.dtos import UserDTO


class IdentityRepository(Protocol):
    def has_any_user(self) -> bool:
        ...

    def get_user_by_login(self, login: str) -> UserDTO | None:
        ...

    def get_password_hash_by_login(self, login: str) -> str | None:
        ...

    def get_user_by_id(self, user_id: UUID) -> UserDTO | None:
        ...

    def create_user(
        self,
        *,
        username: str,
        email: str | None,
        display_name: str | None,
        password_hash: str,
        role: str,
        status: str,
        created_by: UUID | None,
    ) -> UserDTO:
        ...

    def update_user(
        self,
        *,
        user_id: UUID,
        display_name: str | None,
        role: str | None,
        status: str | None,
    ) -> UserDTO | None:
        ...

    def update_password(self, *, user_id: UUID, password_hash: str) -> bool:
        ...

    def update_last_login(self, *, user_id: UUID, logged_in_at: datetime) -> None:
        ...

    def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        ip_hash: str | None,
        user_agent: str | None,
    ) -> None:
        ...

    def get_user_by_session_token_hash(self, token_hash: str, now: datetime) -> UserDTO | None:
        ...

    def revoke_session(self, token_hash: str, revoked_at: datetime) -> bool:
        ...

    def revoke_user_sessions(self, user_id: UUID, revoked_at: datetime) -> None:
        ...

    def list_users(
        self,
        *,
        role: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[UserDTO], int]:
        ...
