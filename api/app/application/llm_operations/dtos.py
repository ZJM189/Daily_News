from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LLMProviderDTO:
    id: UUID
    name: str
    type: str
    base_url: str
    model: str
    api_key_masked: str | None
    timeout_seconds: int
    retry_count: int
    enabled: bool
    is_default: bool
    last_test_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    created_at: datetime
    updated_at: datetime
