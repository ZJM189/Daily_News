from typing import Protocol

from app.application.analytics.dtos import VisitStatsDTO


class VisitAnalyticsRepository(Protocol):
    def record_visit(
        self,
        *,
        visitor_id: str,
        path: str,
        referrer: str | None,
        user_agent: str | None,
    ) -> VisitStatsDTO:
        raise NotImplementedError

    def get_visit_stats(self) -> VisitStatsDTO:
        raise NotImplementedError
