from sqlalchemy.orm import Session

from app.application.analytics.service import VisitAnalyticsService
from app.infrastructure.analytics.repositories import SqlAlchemyVisitAnalyticsRepository


def create_visit_analytics_service(session: Session) -> VisitAnalyticsService:
    return VisitAnalyticsService(SqlAlchemyVisitAnalyticsRepository(session))
