from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SourceCredentialDTO:
    id: UUID
    name: str
    source_type: str
    secret_masked: str
    status: str
    last_test_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SourceDTO:
    id: UUID
    name: str
    type: str
    status: str
    url: str | None
    query_config: dict[str, Any]
    credential_id: UUID | None
    credential_env_key: str | None
    weight: int
    language: str | None
    last_fetched_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
