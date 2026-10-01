from app.application.analytics.dtos import VisitStatsDTO
from app.application.analytics.repositories import VisitAnalyticsRepository


class VisitAnalyticsService:
    def __init__(self, repository: VisitAnalyticsRepository) -> None:
        self._repository = repository

    def record_visit(
        self,
        *,
        visitor_id: str,
        path: str,
        referrer: str | None,
        user_agent: str | None,
    ) -> VisitStatsDTO:
        return self._repository.record_visit(
            visitor_id=visitor_id,
            path=path,
            referrer=referrer,
            user_agent=user_agent,
        )

    def get_visit_stats(self) -> VisitStatsDTO:
        return self._repository.get_visit_stats()
