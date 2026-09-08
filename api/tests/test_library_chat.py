import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.application.content_library.chat import ContentLibraryChatService
from app.application.content_library.chat_intent import (
    LIBRARY_CHAT_REJECTION_MESSAGE,
    LibraryChatIntentDTO,
    classify_library_chat_intent_by_rules,
)
from app.application.content_library.dtos import (
    InterpretedLibraryQueryDTO,
    LibraryChatMessageDTO,
    LibraryChatThreadDTO,
    LibraryItemDTO,
    LibrarySearchChipDTO,
    LibrarySearchLLMDTO,
    LibrarySourceDTO,
    NaturalLanguageLibrarySearchDTO,
)
from app.application.identity.dtos import UserDTO


def test_rule_intent_classifier_blocks_out_of_scope_requests() -> None:
    result = classify_library_chat_intent_by_rules("帮我写一个 Python 爬虫")

    assert result is not None
    assert result.allowed is False
    assert result.intent == "coding"


def test_rule_intent_classifier_blocks_coding_even_when_agent_is_mentioned() -> None:
    result = classify_library_chat_intent_by_rules("Agent 代码怎么写")

    assert result is not None
    assert result.allowed is False
    assert result.intent == "coding"


def test_rule_intent_classifier_allows_ai_library_queries() -> None:
    result = classify_library_chat_intent_by_rules("最近 7 天 RAG 论文")

    assert result is not None
    assert result.allowed is True
    assert result.intent == "library_search"


def test_chat_stream_rejects_out_of_scope_with_fixed_message_without_search() -> None:
    actor = _actor()
    repository = _ChatRepository(actor.id)
    library_service = _LibraryService()
    service = ContentLibraryChatService(
        repository=repository,
        library_repository=_LibraryRepository(),
        library_service=library_service,
        intent_classifier=_IntentClassifier(
            LibraryChatIntentDTO(False, "coding", 0.95, "out of scope", "写代码")
        ),
    )
    thread = service.create_thread(actor=actor)

    events = _events(
        service.stream_message(actor=actor, thread_id=thread.id, content="帮我写一个 Python 爬虫")
    )

    assert library_service.called is False
    assert events[1]["event"] == "rejected"
    assert events[1]["data"]["message"] == LIBRARY_CHAT_REJECTION_MESSAGE
    assert events[-1]["event"] == "done"
    assert repository.messages[-1].role == "assistant"
    assert repository.messages[-1].content == LIBRARY_CHAT_REJECTION_MESSAGE
    assert repository.messages[-1].metadata["mode"] == "rejected"
    assert repository.committed is True
    assert repository.rolled_back is False


def test_chat_stream_searches_library_and_returns_results_event() -> None:
    actor = _actor()
    repository = _ChatRepository(actor.id)
    service = ContentLibraryChatService(
        repository=repository,
        library_repository=_LibraryRepository(),
        library_service=_LibraryService(
            result=NaturalLanguageLibrarySearchDTO(
                mode="llm",
                explanation="查询 RAG 论文",
                interpreted_query=InterpretedLibraryQueryDTO(keyword="RAG", page_size=6),
                chips=[LibrarySearchChipDTO(key="keyword", label="关键词：RAG")],
                items=[_item()],
                total=1,
                page=1,
                page_size=6,
                library_url="/library?keyword=RAG&sort=latest",
                llm=LibrarySearchLLMDTO(provider="Default", model="test-model", confidence=0.9),
            )
        ),
        intent_classifier=_IntentClassifier(
            LibraryChatIntentDTO(True, "library_search", 0.9, "allowed", "RAG 论文")
        ),
    )
    thread = service.create_thread(actor=actor)

    events = _events(service.stream_message(actor=actor, thread_id=thread.id, content="RAG 论文"))

    event_names = [event["event"] for event in events]
    assert event_names[:3] == ["status", "status", "status"]
    assert "delta" in event_names[3:-2]
    assert event_names[-2:] == ["results", "done"]
    assert events[-2]["data"]["meta"]["total"] == 1
    assert events[-2]["data"]["items"][0]["title"] == "EduGuard RAG Tutor"
    assert repository.messages[-1].metadata["mode"] == "llm"
    assert repository.messages[-1].metadata["item_ids"] == [str(events[-2]["data"]["items"][0]["id"])]
    assert repository.committed is True
    assert repository.rolled_back is False


def _events(chunks) -> list[dict[str, object]]:
    events = []
    for chunk in chunks:
        event = None
        data = None
        for line in chunk.strip().splitlines():
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            if line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        events.append({"event": event, "data": data})
    return events


def _actor() -> UserDTO:
    return UserDTO(
        id=uuid4(),
        username="reader",
        email=None,
        display_name=None,
        role="user",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_login_at=None,
    )


def _item() -> LibraryItemDTO:
    now = datetime.now(UTC)
    return LibraryItemDTO(
        id=uuid4(),
        source=LibrarySourceDTO(id=uuid4(), name="arXiv", type="arxiv", url=None),
        title="EduGuard RAG Tutor",
        url="https://example.com/rag",
        canonical_url=None,
        summary_original=None,
        content_snippet="RAG tutor",
        summary_zh="RAG 教学系统",
        importance_zh=None,
        language="en",
        category="research_paper",
        tags=["RAG"],
        status="summarized",
        score=Decimal("88.5"),
        published_at=now,
        collected_at=now,
        summarized_at=now,
        created_at=now,
        updated_at=now,
    )


class _ChatRepository:
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        self.threads: list[LibraryChatThreadDTO] = []
        self.messages: list[LibraryChatMessageDTO] = []
        self.committed = False
        self.rolled_back = False

    def create_thread(self, *, user_id: UUID, title: str) -> LibraryChatThreadDTO:
        now = datetime.now(UTC)
        thread = LibraryChatThreadDTO(
            id=uuid4(),
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        self.threads.append(thread)
        return thread

    def get_thread(self, *, user_id: UUID, thread_id: UUID) -> LibraryChatThreadDTO | None:
        return next(
            (thread for thread in self.threads if thread.id == thread_id and thread.user_id == user_id),
            None,
        )

    def list_threads(self, *, user_id: UUID, limit: int) -> list[LibraryChatThreadDTO]:
        return [thread for thread in self.threads if thread.user_id == user_id][:limit]

    def update_thread_title(self, *, user_id: UUID, thread_id: UUID, title: str) -> None:
        self.threads = [
            LibraryChatThreadDTO(
                id=thread.id,
                user_id=thread.user_id,
                title=title if thread.id == thread_id and thread.user_id == user_id else thread.title,
                created_at=thread.created_at,
                updated_at=datetime.now(UTC),
            )
            for thread in self.threads
        ]

    def create_message(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        role: str,
        content: str,
        metadata: dict[str, object],
    ) -> LibraryChatMessageDTO:
        message = LibraryChatMessageDTO(
            id=uuid4(),
            thread_id=thread_id,
            user_id=user_id,
            role=role,
            content=content,
            metadata=metadata,
            created_at=datetime.now(UTC),
        )
        self.messages.append(message)
        return message

    def list_messages(self, *, user_id: UUID, thread_id: UUID) -> list[LibraryChatMessageDTO]:
        return [
            message
            for message in self.messages
            if message.user_id == user_id and message.thread_id == thread_id
        ]

    def list_recent_messages(
        self,
        *,
        user_id: UUID,
        thread_id: UUID,
        limit: int,
    ) -> list[LibraryChatMessageDTO]:
        return self.list_messages(user_id=user_id, thread_id=thread_id)[-limit:]

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class _LibraryRepository:
    def get_default_llm_provider(self):
        return None


class _LibraryService:
    def __init__(self, result: NaturalLanguageLibrarySearchDTO | None = None) -> None:
        self.result = result
        self.called = False

    def natural_language_search(self, **kwargs):
        self.called = True
        if self.result is None:
            raise AssertionError("library search should not be called")
        return self.result


class _IntentClassifier:
    def __init__(self, result: LibraryChatIntentDTO) -> None:
        self.result = result

    def classify(self, **kwargs) -> LibraryChatIntentDTO:
        return self.result
