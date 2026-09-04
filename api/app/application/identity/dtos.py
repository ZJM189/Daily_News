from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: UUID
    username: str
    email: str | None
    display_name: str | None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


@dataclass(frozen=True, slots=True)
class SessionDTO:
    token: str
    expires_at: datetime
    user: UserDTO

