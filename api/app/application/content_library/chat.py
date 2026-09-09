import json
from collections.abc import Iterator
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.application.content_library.agent import LibraryDatabaseSearchError
from app.application.content_library.chat_intent import (
    LIBRARY_CHAT_REJECTION_MESSAGE,
    LibraryChatIntentClassifier,
)
from app.application.content_library.dtos import (
    LibraryChatMessageDTO,
    LibraryChatThreadDTO,
    LibraryItemDTO,
    NaturalLanguageLibrarySearchDTO,
)
from app.application.content_library.repositories import ContentLibraryRepository
from app.application.content_library.service import ContentLibraryService
from app.application.identity.dtos import UserDTO

DEFAULT_THREAD_TITLE = "新的智能查询"


class ContentLibraryChatRepository(Protocol):
    def create_thread(self, *, user_id: UUID, title: str) -> LibraryChatThreadDTO:
        raise NotImplementedError

    def get_thread(self, *, user_id: UUID, thread_id: UUID) -> LibraryChatThreadDTO | None:
        raise NotImplementedError

    def list_threads(self, *, user_id: UUID, limit: int) -> list[LibraryChatThreadDTO]:
        raise NotImplementedError

    def delete_thread(self, *, user_id: UUID, thread_id: UUID) -> None:
        raise NotImplementedError

    def update_thread_title(self, *, user_id: UUID, thread_id: UUID, title: str) -> None:
        raise NotImplementedError

    def create_message(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        role: str,
        content: str,
        metadata: dict[str, object],
    ) -> LibraryChatMessageDTO:
        raise NotImplementedError

    def list_messages(self, *, user_id: UUID, thread_id: UUID) -> list[LibraryChatMessageDTO]:
        raise NotImplementedError

    def list_recent_messages(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        limit: int,
    ) -> list[LibraryChatMessageDTO]:
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError


class ContentLibraryChatService:
    def __init__(
        self,
        *,
        repository: ContentLibraryChatRepository,
        library_repository: ContentLibraryRepository,
        library_service: ContentLibraryService,
        intent_classifier: LibraryChatIntentClassifier,
    ) -> None:
        self._repository = repository
        self._library_repository = library_repository
        self._library_service = library_service
        self._intent_classifier = intent_classifier

    def create_thread(self, *, actor: UserDTO, title: str | None = None) -> LibraryChatThreadDTO:
        return self._repository.create_thread(
            user_id=actor.id,
            title=_clean_title(title) or DEFAULT_THREAD_TITLE,
        )

    def get_thread(self, *, actor: UserDTO, thread_id: UUID) -> LibraryChatThreadDTO | None:
        return self._repository.get_thread(user_id=actor.id, thread_id=thread_id)

    def list_threads(self, *, actor: UserDTO, limit: int = 20) -> list[LibraryChatThreadDTO]:
        return self._repository.list_threads(user_id=actor.id, limit=min(max(limit, 1), 50))

    def delete_thread(self, *, actor: UserDTO, thread_id: UUID) -> None:
        if self.get_thread(actor=actor, thread_id=thread_id) is None:
            raise ValueError("chat thread not found")
        self._repository.delete_thread(user_id=actor.id, thread_id=thread_id)

    def list_messages(self, *, actor: UserDTO, thread_id: UUID) -> list[LibraryChatMessageDTO]:
        if self.get_thread(actor=actor, thread_id=thread_id) is None:
            raise ValueError("chat thread not found")
        return self._repository.list_messages(user_id=actor.id, thread_id=thread_id)

    def stream_message(
        self,
        *,
        actor: UserDTO,
        thread_id: UUID,
        content: str,
    ) -> Iterator[str]:
        try:
            yield from self._stream_message(actor=actor, thread_id=thread_id, content=content)
            self._repository.commit()
        except Exception:
            self._repository.rollback()
            raise

    def _stream_message(
        self,
        *,
        actor: UserDTO,
        thread_id: UUID,
        content: str,
    ) -> Iterator[str]:
        thread = self.get_thread(actor=actor, thread_id=thread_id)
        if thread is None:
            raise ValueError("chat thread not found")
        content = _clean_message(content)
        if content is None:
            raise ValueError("message content must not be empty")

        previous_messages = self._repository.list_recent_messages(
            user_id=actor.id,
            thread_id=thread_id,
            limit=6,
        )
        user_message = self._repository.create_message(
            user_id=actor.id,
            thread_id=thread_id,
            role="user",
            content=content,
            metadata={},
        )
        if not previous_messages and thread.title == DEFAULT_THREAD_TITLE:
            self._repository.update_thread_title(
                user_id=actor.id,
                thread_id=thread_id,
                title=_title_from_message(content),
            )

        yield _sse("status", {"message": "正在判断查询范围", "message_id": str(user_message.id)})
        intent = self._intent_classifier.classify(
            provider=self._library_repository.get_default_llm_provider(),
            query=content,
            previous_messages=previous_messages,
        )

        if not intent.allowed:
            assistant_message = self._repository.create_message(
                user_id=actor.id,
                thread_id=thread_id,
                role="assistant",
                content=LIBRARY_CHAT_REJECTION_MESSAGE,
                metadata={
                    "mode": "rejected",
                    "intent": intent.intent,
                    "confidence": intent.confidence,
                    "reason": intent.reason,
                },
            )
            yield _sse(
                "rejected",
                {
                    "message": LIBRARY_CHAT_REJECTION_MESSAGE,
                    "message_id": str(assistant_message.id),
                    "intent": intent.intent,
                },
            )
            yield _sse("done", {"message_id": str(assistant_message.id)})
            return

        yield _sse("status", {"message": "正在理解查询意图"})
        try:
            result = self._library_service.natural_language_search(
                actor=actor,
                query=intent.normalized_query or content,
                page_size=6,
            )
        except LibraryDatabaseSearchError:
            message = "信息库查询暂时不可用，请稍后重试。"
            assistant_message = self._repository.create_message(
                user_id=actor.id,
                thread_id=thread_id,
                role="assistant",
                content=message,
                metadata={
                    "mode": "error",
                    "intent": intent.intent,
                    "confidence": intent.confidence,
                    "reason": "library database search failed",
                },
            )
            yield _sse("error", {"message": message, "message_id": str(assistant_message.id)})
            yield _sse("done", {"message_id": str(assistant_message.id)})
            return

        yield _sse("status", {"message": "正在整理结果"})
        assistant_text = _assistant_answer(result)
        assistant_message = self._repository.create_message(
            user_id=actor.id,
            thread_id=thread_id,
            role="assistant",
            content=assistant_text,
            metadata=_metadata_for_result(result, intent=asdict(intent)),
        )
        for chunk in _chunk_text(assistant_text):
            yield _sse("delta", {"message_id": str(assistant_message.id), "text": chunk})

        yield _sse(
            "results",
            {
                "message_id": str(assistant_message.id),
                "items": [_serialize_item(item) for item in result.items],
                "meta": {
                    "page": result.page,
                    "page_size": result.page_size,
                    "total": result.total,
                },
                "library_url": result.library_url,
                "mode": result.mode,
                "chips": [asdict(chip) for chip in result.chips],
                "llm": asdict(result.llm) if result.llm else None,
            },
        )
        yield _sse("done", {"message_id": str(assistant_message.id)})


def _assistant_answer(result: NaturalLanguageLibrarySearchDTO) -> str:
    if result.total == 0:
        return f"{result.explanation}。信息库中没有找到匹配内容；当前不会触发外部实时检索。"

    opening = f"{result.explanation}。共找到 {result.total} 条，先展示 {len(result.items)} 条。"
    lines = [opening]
    for index, item in enumerate(result.items[:3], start=1):
        lines.append(f"{index}. {item.title}（{item.source.name}，{float(item.score):.1f} 分）")
    return "\n".join(lines)


def _metadata_for_result(
    result: NaturalLanguageLibrarySearchDTO,
    *,
    intent: dict[str, object],
) -> dict[str, object]:
    return {
        "mode": result.mode,
        "intent": intent,
        "interpreted_query": _json_safe(result.interpreted_query),
        "chips": [asdict(chip) for chip in result.chips],
        "meta": {
            "page": result.page,
            "page_size": result.page_size,
            "total": result.total,
        },
        "library_url": result.library_url,
        "llm": asdict(result.llm) if result.llm else None,
        "item_ids": [str(item.id) for item in result.items],
        "items": [_serialize_item(item) for item in result.items],
    }


def _serialize_item(item: LibraryItemDTO) -> dict[str, object]:
    return {
        "id": str(item.id),
        "source": {
            "id": str(item.source.id),
            "name": item.source.name,
            "type": item.source.type,
            "url": item.source.url,
        },
        "title": item.title,
        "url": item.url,
        "canonical_url": item.canonical_url,
        "summary_original": item.summary_original,
        "content_snippet": item.content_snippet,
        "summary_zh": item.summary_zh,
        "importance_zh": item.importance_zh,
        "language": item.language,
        "category": item.category,
        "tags": item.tags,
        "status": item.status,
        "score": float(item.score),
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "collected_at": item.collected_at.isoformat(),
        "summarized_at": item.summarized_at.isoformat() if item.summarized_at else None,
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(_json_safe(data), ensure_ascii=False)}\n\n"


def _json_safe(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def _chunk_text(text: str, size: int = 36) -> Iterator[str]:
    for offset in range(0, len(text), size):
        yield text[offset : offset + size]


def _clean_message(value: str) -> str | None:
    text = value.strip()
    return text[:500] if text else None


def _clean_title(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text[:120] if text else None


def _title_from_message(value: str) -> str:
    return value.strip().replace("\n", " ")[:40] or DEFAULT_THREAD_TITLE
