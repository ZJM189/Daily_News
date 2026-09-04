from sqlalchemy.orm import Session

from app.application.content_library.service import ContentLibraryService
from app.infrastructure.content_library.repositories import SqlAlchemyContentLibraryRepository


def create_content_library_service(session: Session) -> ContentLibraryService:
    return ContentLibraryService(SqlAlchemyContentLibraryRepository(session))
