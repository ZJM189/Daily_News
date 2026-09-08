from sqlalchemy.orm import Session

from app.application.content_library.chat import ContentLibraryChatService
from app.application.content_library.service import ContentLibraryService
from app.infrastructure.content_library.chat_repositories import (
    SqlAlchemyContentLibraryChatRepository,
)
from app.infrastructure.content_library.deepagents_client import DeepAgentsLibrarySearchClient
from app.infrastructure.content_library.intent_classifier import (
    OpenAICompatibleLibraryChatIntentClassifier,
)
from app.infrastructure.content_library.repositories import SqlAlchemyContentLibraryRepository


def create_content_library_service(session: Session) -> ContentLibraryService:
    return ContentLibraryService(
        SqlAlchemyContentLibraryRepository(session),
        DeepAgentsLibrarySearchClient(),
    )


def create_content_library_chat_service(session: Session) -> ContentLibraryChatService:
    library_repository = SqlAlchemyContentLibraryRepository(session)
    return ContentLibraryChatService(
        repository=SqlAlchemyContentLibraryChatRepository(session),
        library_repository=library_repository,
        library_service=ContentLibraryService(library_repository, DeepAgentsLibrarySearchClient()),
        intent_classifier=OpenAICompatibleLibraryChatIntentClassifier(),
    )
