from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.application.content_library.chat import ContentLibraryChatRepository
from app.application.content_library.dtos import LibraryChatMessageDTO, LibraryChatThreadDTO
from app.infrastructure.models import LibraryChatMessage, LibraryChatThread


class SqlAlchemyContentLibraryChatRepository(ContentLibraryChatRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_thread(self, *, user_id: UUID, title: str) -> LibraryChatThreadDTO:
        thread = LibraryChatThread(user_id=user_id, title=title)
        self._session.add(thread)
        self._session.flush()
        return self._thread_to_dto(thread)

    def get_thread(self, *, user_id: UUID, thread_id: UUID) -> LibraryChatThreadDTO | None:
        thread = self._session.scalar(
            select(LibraryChatThread).where(
                LibraryChatThread.id == thread_id,
                LibraryChatThread.user_id == user_id,
            )
        )
        return self._thread_to_dto(thread) if thread is not None else None

    def list_threads(self, *, user_id: UUID, limit: int) -> list[LibraryChatThreadDTO]:
        threads = self._session.scalars(
            select(LibraryChatThread)
            .where(LibraryChatThread.user_id == user_id)
            .order_by(LibraryChatThread.updated_at.desc(), LibraryChatThread.created_at.desc())
            .limit(limit)
        ).all()
        return [self._thread_to_dto(thread) for thread in threads]

    def delete_thread(self, *, user_id: UUID, thread_id: UUID) -> None:
        self._session.execute(
            delete(LibraryChatThread).where(
                LibraryChatThread.id == thread_id,
                LibraryChatThread.user_id == user_id,
            )
        )
        self._session.flush()

    def update_thread_title(self, *, user_id: UUID, thread_id: UUID, title: str) -> None:
        self._session.execute(
            update(LibraryChatThread)
            .where(LibraryChatThread.id == thread_id, LibraryChatThread.user_id == user_id)
            .values(title=title, updated_at=func.now())
        )
        self._session.flush()

    def create_message(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        role: str,
        content: str,
        metadata: dict[str, object],
    ) -> LibraryChatMessageDTO:
        message = LibraryChatMessage(
            user_id=user_id,
            thread_id=thread_id,
            role=role,
            content=content,
            message_metadata=metadata,
        )
        self._session.add(message)
        self._session.execute(
            update(LibraryChatThread)
            .where(LibraryChatThread.id == thread_id, LibraryChatThread.user_id == user_id)
            .values(updated_at=func.now())
        )
        self._session.flush()
        return self._message_to_dto(message)

    def list_messages(self, *, user_id: UUID, thread_id: UUID) -> list[LibraryChatMessageDTO]:
        messages = self._session.scalars(
            select(LibraryChatMessage)
            .where(
                LibraryChatMessage.user_id == user_id,
                LibraryChatMessage.thread_id == thread_id,
            )
            .order_by(LibraryChatMessage.created_at.asc(), LibraryChatMessage.id.asc())
        ).all()
        return [self._message_to_dto(message) for message in messages]

    def list_recent_messages(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        limit: int,
    ) -> list[LibraryChatMessageDTO]:
        messages = self._session.scalars(
            select(LibraryChatMessage)
            .where(
                LibraryChatMessage.user_id == user_id,
                LibraryChatMessage.thread_id == thread_id,
            )
            .order_by(LibraryChatMessage.created_at.desc(), LibraryChatMessage.id.desc())
            .limit(limit)
        ).all()
        return [self._message_to_dto(message) for message in reversed(messages)]

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def _thread_to_dto(self, thread: LibraryChatThread) -> LibraryChatThreadDTO:
        return LibraryChatThreadDTO(
            id=thread.id,
            user_id=thread.user_id,
            title=thread.title,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    def _message_to_dto(self, message: LibraryChatMessage) -> LibraryChatMessageDTO:
        return LibraryChatMessageDTO(
            id=message.id,
            thread_id=message.thread_id,
            user_id=message.user_id,
            role=message.role,
            content=message.content,
            metadata=message.message_metadata,
            created_at=message.created_at,
        )
