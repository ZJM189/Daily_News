import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
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
SOURCE_TYPES = {
    "rss",
    "hacker_news",
    "github",
    "arxiv",
    "product_hunt",
    "hugging_face",
}
ITEM_STATUSES = {"collected", "normalized", "deduped", "ranked", "summarized", "selected", "failed"}
SORTS = {"latest", "score", "collected"}

_QUERY_NOISE_TERMS = {
    "ai",
    "arxiv",
    "github",
    "hacker news",
    "hugging face",
    "product hunt",
    "最近",
    "今天",
    "昨天",
    "过去",
    "近",
    "天",
    "周",
    "月",
    "相关",
    "关于",
    "查询",
    "搜索",
    "检索",
    "筛选",
    "论文",
    "研究论文",
    "学术论文",
    "文章",
    "项目",
    "开源",
    "开源项目",
    "产品",
    "产品发布",
    "发布",
    "动态",
    "产业动态",
    "高分",
    "分数",
    "以上",
    "只看",
    "有中文摘要",
    "中文摘要",
    "摘要",
}

_GENERIC_SEARCH_TERMS = {
    "retrieval",
    "augmented",
    "generation",
    "retrieval augmented",
    "retrieval-augmented",
    "knowledge base",
    "向量检索",
    "知识库",
    "人工智能",
}

_FALLBACK_STOP_TERMS = _QUERY_NOISE_TERMS | {
    "and",
    "or",
    "the",
    "with",
    "from",
    "last",
    "days",
    "day",
    "week",
    "weeks",
    "month",
    "months",
    "paper",
    "papers",
    "research",
    "project",
    "projects",
    "product",
    "products",
    "release",
    "releases",
}


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
    terms = tuple(term for term in _clean_terms(query.search_terms) if _is_specific_term(term))
    keyword = _clean_text(query.keyword)
    if not _is_specific_term(keyword):
        keyword = None
    if keyword is None:
        keyword = next((term for term in terms if _is_keyword_candidate(term)), None)
    if keyword is None and not terms:
        fallback_terms = _extract_candidate_terms(fallback_query)
        terms = tuple(fallback_terms)
        keyword = next((term for term in terms if _is_keyword_candidate(term)), None)
    if keyword:
        terms = _dedupe_terms((*terms, keyword))

    published_from = query.published_from
    published_to = query.published_to
    if published_from and published_to and published_from > published_to:
        raise LibrarySearchAgentSchemaError("published_from is after published_to")

    return InterpretedLibraryQueryDTO(
        keyword=keyword,
        search_terms=terms,
        category=(
            query.category
            if query.category in CATEGORY_CODES
            else _infer_category(fallback_query)
        ),
        source_type=(
            query.source_type
            if query.source_type in SOURCE_TYPES
            else _infer_source_type(fallback_query)
        ),
        source_id=query.source_id,
        status=query.status if query.status in ITEM_STATUSES else None,
        published_from=published_from,
        published_to=published_to,
        min_score=_score_or_none(query.min_score),
        has_summary=query.has_summary if isinstance(query.has_summary, bool) else None,
        sort=query.sort if query.sort in SORTS else "latest",
        page_size=_bounded_page_size(query.page_size or page_size),
    )


def fallback_interpreted_query(
    *,
    query: str,
    page_size: int,
    current_time: datetime | None = None,
) -> InterpretedLibraryQueryDTO:
    terms = _extract_candidate_terms(query)
    keyword = next((term for term in terms if _is_keyword_candidate(term)), None)
    published_from, published_to = _relative_time_range(
        query,
        current_time=current_time or datetime.now(UTC),
    )
    min_score = _extract_min_score(query)
    has_summary = True if "摘要" in query and "没有摘要" not in query else None
    sort = (
        "score"
        if min_score is not None
        or any(marker in query.casefold() for marker in ("高分", "最高分", "score"))
        else "latest"
    )
    return InterpretedLibraryQueryDTO(
        keyword=keyword,
        search_terms=terms,
        category=_infer_category(query),
        source_type=_infer_source_type(query),
        published_from=published_from,
        published_to=published_to,
        min_score=min_score,
        has_summary=has_summary,
        sort=sort,
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


def _is_specific_term(value: str | None) -> bool:
    if not value:
        return False
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    if not normalized or len(normalized) > 80:
        return False
    if any(marker in normalized for marker in ("最近", "过去", "相关", "论文", "项目", "产品发布")):
        return False
    return normalized not in _GENERIC_SEARCH_TERMS and normalized not in _QUERY_NOISE_TERMS


def _is_keyword_candidate(value: str) -> bool:
    return _is_specific_term(value)


def _extract_candidate_terms(query: str) -> tuple[str, ...]:
    normalized_query = query
    for source_phrase in (
        "hacker news",
        "hugging face",
        "product hunt",
        "github",
        "arxiv",
    ):
        normalized_query = re.sub(
            re.escape(source_phrase),
            " ",
            normalized_query,
            flags=re.IGNORECASE,
        )

    candidates = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", normalized_query)
    terms: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        cleaned = candidate.strip(" .,#")
        normalized = cleaned.casefold()
        if (
            len(cleaned) < 2
            or normalized in _FALLBACK_STOP_TERMS
            or normalized in _GENERIC_SEARCH_TERMS
            or normalized in seen
        ):
            continue
        seen.add(normalized)
        terms.append(cleaned)
        if len(terms) >= 8:
            break
    return tuple(terms)


def _infer_category(query: str) -> str | None:
    text = query.casefold()
    if any(marker in text for marker in ("研究论文", "学术论文", "论文", "paper", "research")):
        return "research_paper"
    if any(marker in text for marker in ("开源项目", "开源", "github", "open source")):
        return "open_source"
    if any(marker in text for marker in ("模型公司", "openai", "deepseek", "anthropic", "deepmind")):
        return "model_company"
    return None


def _infer_source_type(query: str) -> str | None:
    text = query.casefold()
    if "github" in text:
        return "github"
    if "hacker news" in text:
        return "hacker_news"
    if "hugging face" in text:
        return "hugging_face"
    if "product hunt" in text:
        return "product_hunt"
    # The current arXiv source is configured as an RSS feed. Category inference
    # handles arXiv papers without incorrectly filtering source_type=arxiv.
    return None


def _relative_time_range(
    query: str,
    *,
    current_time: datetime,
) -> tuple[datetime | None, datetime | None]:
    match = re.search(r"(?:最近|过去|近)\s*(\d+)\s*天", query)
    if match is None:
        return None, None
    days = max(1, min(int(match.group(1)), 365))
    return current_time - timedelta(days=days), current_time


def _extract_min_score(query: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:分|分数)?\s*(?:以上|及以上|\+)", query)
    if match is None:
        return None
    return min(max(float(match.group(1)), 0), 100)


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
