from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.content_library.agent import (
    LibraryDatabaseSearchError,
    LibrarySearchAgentSchemaError,
    fallback_interpreted_query,
    parse_agent_payload,
    sanitize_interpreted_query,
)
from app.application.content_library.dtos import (
    InterpretedLibraryQueryDTO,
    LibraryAgentParseDTO,
    LibraryLLMProviderDTO,
)
from app.application.content_library.service import ContentLibraryService
from app.application.identity.dtos import UserDTO
from app.interfaces.http.schemas import NaturalLanguageLibrarySearchRequest


def test_agent_payload_is_sanitized_to_allowed_query_fields() -> None:
    parsed = parse_agent_payload(
        {
            "keyword": " RAG ",
            "search_terms": ["RAG", "retrieval augmented generation", "RAG"],
            "category": "research_paper",
            "source_type": "not-allowed",
            "min_score": 80,
            "sort": "score",
            "confidence": 0.9,
            "explanation": "查询高分 RAG 论文",
        },
        fallback_query="原始查询",
        page_size=10,
    )

    assert parsed.interpreted_query.keyword == "RAG"
    assert parsed.interpreted_query.search_terms == ("RAG", "retrieval augmented generation")
    assert parsed.interpreted_query.category == "research_paper"
    assert parsed.interpreted_query.source_type is None
    assert parsed.interpreted_query.min_score == 80


def test_invalid_date_order_is_rejected() -> None:
    with pytest.raises(LibrarySearchAgentSchemaError):
        sanitize_interpreted_query(
            InterpretedLibraryQueryDTO(
                published_from=datetime(2026, 9, 8, tzinfo=UTC),
                published_to=datetime(2026, 9, 7, tzinfo=UTC),
            ),
            fallback_query="RAG",
            page_size=10,
        )


def test_fallback_query_keeps_original_text() -> None:
    parsed = fallback_interpreted_query(query="  最近的 RAG 论文  ", page_size=50)

    assert parsed.keyword == "最近的 RAG 论文"
    assert parsed.search_terms == ("最近的 RAG 论文",)
    assert parsed.page_size == 20


def test_natural_language_request_rejects_blank_query() -> None:
    with pytest.raises(ValueError):
        NaturalLanguageLibrarySearchRequest(query="   ")


def test_agent_uses_database_search_tool() -> None:
    provider = LibraryLLMProviderDTO(
        id=uuid4(),
        name="Default",
        base_url="https://llm.example/v1",
        model="test-model",
        api_key="secret",
        timeout_seconds=10,
        retry_count=1,
    )
    actor = UserDTO(
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

    class Repository:
        def __init__(self) -> None:
            self.queries = []

        def get_default_llm_provider(self):
            return provider

        def search_items(self, *, query, page, page_size):
            self.queries.append((query, page, page_size))
            return [], 0

        def log_llm_query(self, **kwargs):
            self.log = kwargs

    class Agent:
        def interpret_query(self, *, database_search_tool, **kwargs):
            database_search_tool(
                keyword="RAG",
                search_terms=["retrieval augmented generation"],
                category="research_paper",
                page_size=5,
            )
            return LibraryAgentParseDTO(
                interpreted_query=InterpretedLibraryQueryDTO(
                    keyword="RAG",
                    search_terms=("retrieval augmented generation",),
                    category="research_paper",
                    page_size=5,
                ),
                explanation="查询 RAG 论文",
                confidence=0.9,
                latency_ms=20,
            )

    repository = Repository()
    result = ContentLibraryService(repository, Agent()).natural_language_search(
        actor=actor,
        query="最近的 RAG 论文",
        page_size=10,
    )

    assert result.mode == "llm"
    assert result.total == 0
    assert repository.queries[0][0].category == "research_paper"
    assert repository.queries[0][0].search_terms == (
        "retrieval augmented generation",
        "RAG",
    )


def test_database_errors_are_not_hidden_by_agent_fallback() -> None:
    provider = LibraryLLMProviderDTO(
        id=uuid4(),
        name="Default",
        base_url="https://llm.example/v1",
        model="test-model",
        api_key="secret",
        timeout_seconds=10,
        retry_count=1,
    )
    actor = UserDTO(
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

    class Repository:
        def get_default_llm_provider(self):
            return provider

        def search_items(self, *, query, page, page_size):
            raise RuntimeError("database unavailable")

        def log_llm_query(self, **kwargs):
            raise AssertionError("database errors must not be logged through the same session")

    class Agent:
        def interpret_query(self, *, database_search_tool, **kwargs):
            database_search_tool(keyword="RAG", page_size=5)
            return LibraryAgentParseDTO(
                interpreted_query=InterpretedLibraryQueryDTO(keyword="RAG"),
                explanation="查询 RAG",
                confidence=0.8,
            )

    with pytest.raises(LibraryDatabaseSearchError):
        ContentLibraryService(repository=Repository(), agent=Agent()).natural_language_search(
            actor=actor,
            query="RAG",
            page_size=10,
        )
