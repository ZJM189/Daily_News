from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.identity.dtos import UserDTO
from app.application.identity.repositories import IdentityRepository
from app.infrastructure.models import AuthSession, User, UserPreference, UserRole, UserStatus


class SqlAlchemyIdentityRepository(IdentityRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def has_any_user(self) -> bool:
        return self._session.scalar(select(User.id).limit(1)) is not None

    def get_user_by_login(self, login: str) -> UserDTO | None:
        user = self._find_user_by_login(login)
        return self._to_dto(user) if user is not None else None

    def get_password_hash_by_login(self, login: str) -> str | None:
        user = self._find_user_by_login(login)
        return user.password_hash if user is not None else None

    def get_user_by_id(self, user_id: UUID) -> UserDTO | None:
        user = self._session.get(User, user_id)
        return self._to_dto(user) if user is not None else None

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
        user = User(
            username=username,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            role=UserRole(role),
            status=UserStatus(status),
            created_by=created_by,
        )
        self._session.add(user)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValueError("username or email already exists") from exc

        self._session.add(UserPreference(user_id=user.id))
        self._session.flush()
        return self._to_dto(user)

    def update_user(
        self,
        *,
        user_id: UUID,
        display_name: str | None,
        role: str | None,
        status: str | None,
    ) -> UserDTO | None:
        values: dict[str, object] = {}
        if display_name is not None:
            values["display_name"] = display_name
        if role is not None:
            values["role"] = UserRole(role)
        if status is not None:
            values["status"] = UserStatus(status)
        if not values:
            return self.get_user_by_id(user_id)

        values["updated_at"] = func.now()
        result = self._session.execute(update(User).where(User.id == user_id).values(**values))
        if result.rowcount == 0:
            return None
        self._session.flush()
        return self.get_user_by_id(user_id)

    def update_password(self, *, user_id: UUID, password_hash: str) -> bool:
        result = self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash, updated_at=func.now())
        )
        self._session.flush()
        return result.rowcount > 0

    def update_last_login(self, *, user_id: UUID, logged_in_at: datetime) -> None:
        self._session.execute(
            update(User).where(User.id == user_id).values(last_login_at=logged_in_at)
        )
        self._session.flush()

    def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        ip_hash: str | None,
        user_agent: str | None,
    ) -> None:
        self._session.add(
            AuthSession(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                ip_hash=ip_hash,
                user_agent=user_agent,
            )
        )
        self._session.flush()

    def get_user_by_session_token_hash(self, token_hash: str, now: datetime) -> UserDTO | None:
        statement = (
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                User.status == UserStatus.ACTIVE,
            )
        )
        user = self._session.scalar(statement)
        return self._to_dto(user) if user is not None else None

    def revoke_session(self, token_hash: str, revoked_at: datetime) -> bool:
        result = self._session.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == token_hash, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        self._session.flush()
        return result.rowcount > 0

    def revoke_user_sessions(self, user_id: UUID, revoked_at: datetime) -> None:
        self._session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        self._session.flush()

    def list_users(
        self,
        *,
        role: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[UserDTO], int]:
        conditions = []
        if role is not None:
            conditions.append(User.role == role)
        if status is not None:
            conditions.append(User.status == status)
        if keyword:
            like_keyword = f"%{keyword}%"
            conditions.append(
                or_(
                    User.username.ilike(like_keyword),
                    User.email.ilike(like_keyword),
                    User.display_name.ilike(like_keyword),
                )
            )

        total_statement = select(func.count()).select_from(User)
        list_statement = select(User).order_by(User.created_at.desc())
        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self._session.scalar(total_statement) or 0
        users = self._session.scalars(
            list_statement.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [self._to_dto(user) for user in users], total

    def _find_user_by_login(self, login: str) -> User | None:
        normalized_login = login.strip()
        return self._session.scalar(
            select(User).where(
                or_(
                    User.username == normalized_login,
                    User.email == normalized_login.lower(),
                )
            )
        )

    def _to_dto(self, user: User) -> UserDTO:
        return UserDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            role=str(user.role.value if hasattr(user.role, "value") else user.role),
            status=str(user.status.value if hasattr(user.status, "value") else user.status),
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        )
