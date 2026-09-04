from datetime import datetime
from typing import Protocol

from app.application.ingestion.dtos import CollectableSourceDTO, RawCollectedItem


class Collector(Protocol):
    source_type: str

    def collect(
        self,
        source: CollectableSourceDTO,
        *,
        since: datetime | None,
    ) -> list[RawCollectedItem]:
        raise NotImplementedError


class CollectorRegistry:
    def __init__(self, collectors: list[Collector]) -> None:
        self._collectors = {collector.source_type: collector for collector in collectors}

    def get(self, source_type: str) -> Collector | None:
        return self._collectors.get(source_type)
