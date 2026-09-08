from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

from app.application.content_library.agent import (
    LibraryDatabaseSearchError,
    LibrarySearchAgentClient,
    fallback_interpreted_query,
    sanitize_interpreted_query,
)
from app.application.content_library.dtos import (
    LibraryAnalyticsDTO,
    LibraryAnalyticsQuery,
    LibraryItemDTO,
    LibraryLLMProviderDTO,
    LibrarySearchChipDTO,
    LibrarySearchLLMDTO,
    LibrarySearchQuery,
    NaturalLanguageLibrarySearchDTO,
)
from app.application.content_library.repositories import ContentLibraryRepository
from app.application.identity.dtos import UserDTO


class ContentLibraryService:
    def __init__(
        self,
        repository: ContentLibraryRepository,
        agent: LibrarySearchAgentClient | None = None,
    ) -> None:
        self._repository = repository
        self._agent = agent

    def search_items(
        self,
        *,
        actor: UserDTO,
        query: LibrarySearchQuery,
        page: int,
        page_size: int,
    ) -> tuple[list[LibraryItemDTO], int]:
        del actor
        normalized_query = LibrarySearchQuery(
            keyword=_clean_text(query.keyword),
            search_terms=_clean_terms(query.search_terms),
            category=query.category,
            source_type=query.source_type,
            source_id=query.source_id,
            status=query.status,
            published_from=query.published_from,
            published_to=query.published_to,
            min_score=query.min_score,
            has_summary=query.has_summary,
            sort=query.sort,
        )
        return self._repository.search_items(
            query=normalized_query,
            page=page,
            page_size=page_size,
        )

    def get_item(self, *, actor: UserDTO, item_id: UUID) -> LibraryItemDTO | None:
        del actor
        return self._repository.get_item(item_id)

    def get_analytics(
        self,
        *,
        actor: UserDTO,
        query: LibraryAnalyticsQuery,
    ) -> LibraryAnalyticsDTO:
        del actor
        normalized_query = LibraryAnalyticsQuery(
            keyword=_clean_text(query.keyword),
            search_terms=_clean_terms(query.search_terms),
            category=query.category,
            source_type=query.source_type,
            source_id=query.source_id,
            status=query.status,
            min_score=query.min_score,
            has_summary=query.has_summary,
            window_days=query.window_days if query.window_days and query.window_days > 0 else None,
        )
        return self._repository.get_analytics(query=normalized_query)

    def natural_language_search(
        self,
        *,
        actor: UserDTO,
        query: str,
        page_size: int,
    ) -> NaturalLanguageLibrarySearchDTO:
        query = _clean_text(query)
        if not query:
            raise ValueError("query must not be empty")
        page_size = min(max(page_size, 1), 20)

        provider = self._repository.get_default_llm_provider()
        started_at = datetime.now(UTC)
        tool_result: dict[str, object] = {}
        if provider is None or self._agent is None:
            return self._fallback_natural_language_search(
                actor=actor,
                query=query,
                page_size=page_size,
                provider=provider,
                started_at=started_at,
                error=RuntimeError("deepagents or default llm provider is unavailable"),
            )

        try:
            database_search_tool = self._database_search_tool(
                actor=actor,
                fallback_query=query,
                result_holder=tool_result,
            )
            parsed = self._agent.interpret_query(
                provider=provider,
                query=query,
                page_size=page_size,
                current_time=started_at,
                database_search_tool=database_search_tool,
            )
            database_error = tool_result.get("database_error")
            if isinstance(database_error, BaseException):
                raise LibraryDatabaseSearchError("library database search failed") from database_error
            parsed_query = sanitize_interpreted_query(
                parsed.interpreted_query,
                fallback_query=query,
                page_size=page_size,
            )
            tool_value = tool_result.get("value")
            if not isinstance(tool_value, tuple):
                raise TypeError("deepagents did not call the database search tool")
            items, total = tool_value
            if not isinstance(items, list) or not isinstance(total, int):
                raise TypeError("deepagents returned an invalid database search result")
            interpreted_query = tool_result.get("query")
            if not isinstance(interpreted_query, type(parsed_query)):
                interpreted_query = parsed_query
        except LibraryDatabaseSearchError:
            raise
        except Exception as exc:  # noqa: BLE001
            database_error = tool_result.get("database_error")
            if isinstance(database_error, BaseException):
                raise LibraryDatabaseSearchError("library database search failed") from database_error
            return self._fallback_natural_language_search(
                actor=actor,
                query=query,
                page_size=page_size,
                provider=provider,
                started_at=started_at,
                error=exc,
            )

        self._repository.log_llm_query(
            provider=provider,
            actor_id=actor.id,
            status="success",
            latency_ms=parsed.latency_ms,
            error_message=None,
        )
        return NaturalLanguageLibrarySearchDTO(
            mode="llm",
            explanation=parsed.explanation,
            interpreted_query=interpreted_query,
            chips=_chips_for_query(interpreted_query),
            items=items,
            total=total,
            page=1,
            page_size=page_size,
            library_url=_library_url(interpreted_query),
            llm=LibrarySearchLLMDTO(
                provider=provider.name,
                model=provider.model,
                confidence=parsed.confidence,
            ),
        )

    def _fallback_natural_language_search(
        self,
        *,
        actor: UserDTO,
        query: str,
        page_size: int,
        provider: LibraryLLMProviderDTO | None,
        started_at: datetime,
        error: BaseException,
    ) -> NaturalLanguageLibrarySearchDTO:
        interpreted_query = fallback_interpreted_query(query=query, page_size=page_size)
        items, total = self.search_items(
            actor=actor,
            query=LibrarySearchQuery(
                keyword=interpreted_query.keyword,
                search_terms=interpreted_query.search_terms,
            ),
            page=1,
            page_size=page_size,
        )
        self._repository.log_llm_query(
            provider=provider,
            actor_id=actor.id,
            status="failed",
            latency_ms=round((datetime.now(UTC) - started_at).total_seconds() * 1000),
            error_message=str(error)[:4000],
        )
        return NaturalLanguageLibrarySearchDTO(
            mode="fallback",
            explanation="智能解析暂不可用，已按关键词检索",
            interpreted_query=interpreted_query,
            chips=_chips_for_query(interpreted_query),
            items=items,
            total=total,
            page=1,
            page_size=page_size,
            library_url=_library_url(interpreted_query),
            llm=None,
        )

    def _database_search_tool(
        self,
        *,
        actor: UserDTO,
        fallback_query: str,
        result_holder: dict[str, object],
    ):
        def search_library_database(
            *,
            keyword: str | None = None,
            search_terms: list[str] | None = None,
            category: str | None = None,
            source_type: str | None = None,
            source_id: str | None = None,
            status: str | None = None,
            published_from: str | None = None,
            published_to: str | None = None,
            min_score: float | None = None,
            has_summary: bool | None = None,
            sort: str = "latest",
            page_size: int = 10,
        ) -> dict[str, object]:
            """Search read-only records already stored in the Daily News library."""
            from app.application.content_library.agent import (
                InterpretedLibraryQueryDTO,
                _datetime_or_none,
                _uuid_or_none,
            )

            interpreted = sanitize_interpreted_query(
                InterpretedLibraryQueryDTO(
                    keyword=keyword,
                    search_terms=tuple(search_terms or ()),
                    category=category,
                    source_type=source_type,
                    source_id=_uuid_or_none(source_id),
                    status=status,
                    published_from=_datetime_or_none(published_from),
                    published_to=_datetime_or_none(published_to),
                    min_score=min_score,
                    has_summary=has_summary,
                    sort=sort,
                    page_size=page_size,
                ),
                fallback_query=fallback_query,
                page_size=page_size,
            )
            result_holder["query"] = interpreted
            try:
                result_holder["value"] = self.search_items(
                    actor=actor,
                    query=LibrarySearchQuery(
                        keyword=interpreted.keyword,
                        search_terms=interpreted.search_terms,
                        category=interpreted.category,
                        source_type=interpreted.source_type,
                        source_id=interpreted.source_id,
                        status=interpreted.status,
                        published_from=interpreted.published_from,
                        published_to=interpreted.published_to,
                        min_score=interpreted.min_score,
                        has_summary=interpreted.has_summary,
                        sort=interpreted.sort,
                    ),
                    page=1,
                    page_size=interpreted.page_size,
                )
            except Exception as exc:
                result_holder["database_error"] = exc
                raise

            items, total = result_holder["value"]
            return {
                "total": total,
                "items": [
                    {
                        "id": str(item.id),
                        "title": item.title,
                        "source": item.source.name,
                        "category": item.category,
                        "score": float(item.score),
                        "published_at": item.published_at.isoformat()
                        if item.published_at
                        else None,
                    }
                    for item in items
                ],
            }

        return search_library_database


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_terms(value: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(term.strip() for term in value if term and term.strip())[:8]


def _chips_for_query(query) -> list[LibrarySearchChipDTO]:
    chips: list[LibrarySearchChipDTO] = []
    if query.keyword:
        chips.append(LibrarySearchChipDTO(key="keyword", label=f"关键词：{query.keyword}"))
    if query.category:
        chips.append(LibrarySearchChipDTO(key="category", label=f"分类：{query.category}"))
    if query.source_type:
        chips.append(LibrarySearchChipDTO(key="source_type", label=f"来源：{query.source_type}"))
    if query.min_score is not None:
        chips.append(LibrarySearchChipDTO(key="min_score", label=f"分数：{query.min_score:g}+"))
    if query.sort != "latest":
        chips.append(LibrarySearchChipDTO(key="sort", label=f"排序：{query.sort}"))
    return chips


def _library_url(query) -> str:
    params: dict[str, str] = {}
    if query.keyword:
        params["keyword"] = query.keyword
    if query.search_terms:
        params["search_terms"] = ",".join(query.search_terms)
    if query.category:
        params["category"] = query.category
    if query.source_type:
        params["source_type"] = query.source_type
    if query.source_id:
        params["source_id"] = str(query.source_id)
    if query.status:
        params["status"] = query.status
    if query.published_from:
        params["published_from"] = query.published_from.isoformat()
    if query.published_to:
        params["published_to"] = query.published_to.isoformat()
    if query.min_score is not None:
        params["min_score"] = f"{query.min_score:g}"
    if query.has_summary is not None:
        params["has_summary"] = str(query.has_summary).lower()
    params["sort"] = query.sort
    return "/library?" + urlencode(params)
