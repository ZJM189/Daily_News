from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class DomainEvent:
    occurred_at: datetime = datetime.now(UTC)
