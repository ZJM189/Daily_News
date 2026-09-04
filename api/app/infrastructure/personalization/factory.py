from sqlalchemy.orm import Session

from app.application.personalization.service import PersonalizationService
from app.infrastructure.personalization.repositories import SqlAlchemyPersonalizationRepository


def create_personalization_service(session: Session) -> PersonalizationService:
    return PersonalizationService(SqlAlchemyPersonalizationRepository(session))
