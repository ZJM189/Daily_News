from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.application.analytics.dtos import VisitStatsDTO
from app.application.analytics.repositories import VisitAnalyticsRepository
from app.infrastructure.models import VisitEvent

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class SqlAlchemyVisitAnalyticsRepository(VisitAnalyticsRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_visit(
        self,
        *,
        visitor_id: str,
        path: str,
        referrer: str | None,
        user_agent: str | None,
    ) -> VisitStatsDTO:
        self._session.add(
            VisitEvent(
                visitor_id=visitor_id,
                path=path,
                referrer=referrer,
                user_agent=user_agent,
            )
        )
        self._session.flush()
        return self.get_visit_stats()

    def get_visit_stats(self) -> VisitStatsDTO:
        today_start = datetime.combine(
            datetime.now(SHANGHAI_TZ).date(),
            time.min,
            tzinfo=SHANGHAI_TZ,
        )
        total_visits = self._session.scalar(select(func.count(VisitEvent.id))) or 0
        today_visits = (
            self._session.scalar(
                select(func.count(VisitEvent.id)).where(VisitEvent.created_at >= today_start)
            )
            or 0
        )
        unique_visitors = (
            self._session.scalar(select(func.count(distinct(VisitEvent.visitor_id)))) or 0
        )
        today_unique_visitors = (
            self._session.scalar(
                select(func.count(distinct(VisitEvent.visitor_id))).where(
                    VisitEvent.created_at >= today_start
                )
            )
            or 0
        )
        return VisitStatsDTO(
            total_visits=int(total_visits),
            today_visits=int(today_visits),
            unique_visitors=int(unique_visitors),
            today_unique_visitors=int(today_unique_visitors),
        )
