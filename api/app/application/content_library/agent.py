from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.content_library.dtos import (
    InterpretedLibraryQueryDTO,
    LibraryAgentParseDTO,
    LibraryLLMProviderDTO,
)

CATEGORY_CODES = {
    "model_company",
    "open_source",
    "research_paper",
    "product_launch",
    "community",
    "industry_funding",
    "other",
}
SOURCE_TYPES = {"rss", "hacker_news", "github", "arxiv", "product_hunt", "hugging_face"}
ITEM_STATUSES = {"collected", "normalized", "deduped", "ranked", "summarized", "selected", "failed"}
SORTS = {"latest", "score", "collected"}


class LibrarySearchAgentSchemaError(ValueError):
    pass


class LibraryDatabaseSearchError(RuntimeError):
    pass


DatabaseSearchTool = Callable[..., dict[str, Any]]


class LibrarySearchAgentClient(Protocol):
    def interpret_query(
        self,
        *,
        provider: LibraryLLMProviderDTO,
        query: str,
        page_size: int,
        current_time: datetime,
        database_search_tool: DatabaseSearchTool,
    ) -> LibraryAgentParseDTO:
        raise NotImplementedError


def parse_agent_payload(
    payload: dict[str, Any],
    *,
    fallback_query: str,
    page_size: int,
) -> LibraryAgentParseDTO:
    interpreted_payload = payload.get("interpreted_query")
    if not isinstance(interpreted_payload, dict):
        interpreted_payload = payload

    interpreted_query = sanitize_interpreted_query(
        _interpreted_from_payload(interpreted_payload),
        fallback_query=fallback_query,
        page_size=page_size,
    )
    explanation = _clean_text(payload.get("explanation"))
    confidence = _confidence(payload.get("confidence"))
    return LibraryAgentParseDTO(
        interpreted_query=interpreted_query,
        explanation=explanation or _explanation_for_query(interpreted_query),
        confidence=confidence,
        input_tokens=_optional_int(payload.get("input_tokens")),
        output_tokens=_optional_int(payload.get("output_tokens")),
        latency_ms=_optional_int(payload.get("latency_ms")),
    )


def sanitize_interpreted_query(
    query: InterpretedLibraryQueryDTO,
    *,
    fallback_query: str,
    page_size: int,
) -> InterpretedLibraryQueryDTO:
    keyword = _clean_text(query.keyword) or _clean_text(fallback_query)
    terms = _clean_terms(query.search_terms)
    if keyword:
        terms = _dedupe_terms((*terms, keyword))

    published_from = query.published_from
    published_to = query.published_to
    if published_from and published_to and published_from > published_to:
        raise LibrarySearchAgentSchemaError("published_from is after published_to")

    return InterpretedLibraryQueryDTO(
        keyword=keyword,
        search_terms=terms,
        category=query.category if query.category in CATEGORY_CODES else None,
        source_type=query.source_type if query.source_type in SOURCE_TYPES else None,
        source_id=query.source_id,
        status=query.status if query.status in ITEM_STATUSES else None,
        published_from=published_from,
        published_to=published_to,
        min_score=_score_or_none(query.min_score),
        has_summary=query.has_summary if isinstance(query.has_summary, bool) else None,
        sort=query.sort if query.sort in SORTS else "latest",
        page_size=_bounded_page_size(query.page_size or page_size),
    )


def fallback_interpreted_query(*, query: str, page_size: int) -> InterpretedLibraryQueryDTO:
    keyword = _clean_text(query)
    return InterpretedLibraryQueryDTO(
        keyword=keyword,
        search_terms=(keyword,) if keyword else (),
        sort="latest",
        page_size=_bounded_page_size(page_size),
    )


def _interpreted_from_payload(payload: dict[str, Any]) -> InterpretedLibraryQueryDTO:
    return InterpretedLibraryQueryDTO(
        keyword=_clean_text(payload.get("keyword")),
        search_terms=_clean_terms(payload.get("search_terms")),
        category=_clean_text(payload.get("category")),
        source_type=_clean_text(payload.get("source_type")),
        source_id=_uuid_or_none(payload.get("source_id")),
        status=_clean_text(payload.get("status")),
        published_from=_datetime_or_none(payload.get("published_from")),
        published_to=_datetime_or_none(payload.get("published_to")),
        min_score=_optional_float(payload.get("min_score")),
        has_summary=payload.get("has_summary") if isinstance(payload.get("has_summary"), bool) else None,
        sort=_clean_text(payload.get("sort")) or "latest",
        page_size=_bounded_page_size(payload.get("page_size")),
    )


def _explanation_for_query(query: InterpretedLibraryQueryDTO) -> str:
    if query.keyword:
        return f"按“{query.keyword}”查询已入库内容"
    return "查询已入库内容"


def _clean_text(value: object, *, max_length: int = 200) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned[:max_length] if cleaned else None


def _clean_terms(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return _dedupe_terms((_clean_text(value) or "",))
    if not isinstance(value, (list, tuple)):
        return ()
    terms = tuple(_clean_text(item, max_length=80) or "" for item in value)
    return _dedupe_terms(terms)


def _dedupe_terms(terms: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for term in terms:
        cleaned = term.strip()
        key = cleaned.casefold()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned[:80])
        if len(result) >= 8:
            break
    return tuple(result)


def _datetime_or_none(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise LibrarySearchAgentSchemaError("invalid datetime in agent payload") from exc


def _uuid_or_none(value: object) -> UUID | None:
    if value is None or value == "":
        return None
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise LibrarySearchAgentSchemaError("invalid source_id in agent payload") from exc


def _score_or_none(value: object) -> float | None:
    score = _optional_float(value)
    if score is None:
        return None
    if score < 0 or score > 100:
        raise LibrarySearchAgentSchemaError("min_score out of range")
    return score


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise LibrarySearchAgentSchemaError("invalid numeric field in agent payload") from exc


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bounded_page_size(value: object) -> int:
    try:
        size = int(value)
    except (TypeError, ValueError):
        size = 10
    return min(max(size, 1), 20)


def _confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5
    return min(max(confidence, 0.0), 1.0)
