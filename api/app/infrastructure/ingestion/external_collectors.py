import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.application.ingestion.collectors import Collector
from app.application.ingestion.dtos import CollectableSourceDTO, RawCollectedItem
from app.infrastructure.ingestion.rss import parse_rss_items

USER_AGENT = "DailyNewsBot/0.1"


class HackerNewsCollector(Collector):
    source_type = "hacker_news"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        source: CollectableSourceDTO,
        *,
        since: datetime | None,
    ) -> list[RawCollectedItem]:
        params: dict[str, object] = {
            "query": _text_config(source.query_config, "query", default="AI OR LLM"),
            "tags": _text_config(source.query_config, "tags", default="story"),
            "hitsPerPage": _int_config(source.query_config, "limit", default=50, maximum=100),
        }
        if since is not None:
            params["numericFilters"] = f"created_at_i>{int(since.timestamp())}"
        response = httpx.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params=params,
            timeout=self._timeout_seconds,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return parse_hacker_news_hits(response.json(), since=since)


class GitHubCollector(Collector):
    source_type = "github"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        source: CollectableSourceDTO,
        *,
        since: datetime | None,
    ) -> list[RawCollectedItem]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
        token = _env_token(source)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = httpx.get(
            "https://api.github.com/search/repositories",
            params={
                "q": _text_config(source.query_config, "query", default="AI LLM"),
                "sort": _text_config(source.query_config, "sort", default="updated"),
                "order": "desc",
                "per_page": _int_config(source.query_config, "limit", default=30, maximum=100),
            },
            timeout=self._timeout_seconds,
            headers=headers,
        )
        response.raise_for_status()
        return parse_github_repositories(response.json(), since=since)


class ArxivCollector(Collector):
    source_type = "arxiv"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        source: CollectableSourceDTO,
        *,
        since: datetime | None,
    ) -> list[RawCollectedItem]:
        response = httpx.get(
            source.url or "https://export.arxiv.org/api/query",
            params={
                "search_query": _text_config(
                    source.query_config,
                    "search_query",
                    default="all:artificial intelligence OR all:large language model",
                ),
                "start": 0,
                "max_results": _int_config(source.query_config, "limit", default=30, maximum=100),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            },
            timeout=self._timeout_seconds,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return parse_rss_items(response.text, since=since)


class ProductHuntCollector(Collector):
    source_type = "product_hunt"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        source: CollectableSourceDTO,
        *,
        since: datetime | None,
    ) -> list[RawCollectedItem]:
        token = _env_token(source)
        if not token:
            raise ValueError("product_hunt source requires credential_env_key or token_env")

        query = """
        query DailyNewsProductHunt($first: Int!) {
          posts(first: $first, order: RANKING) {
            edges {
              node {
                id
                name
                tagline
                url
                createdAt
                votesCount
                commentsCount
                user { name }
                topics(first: 5) { edges { node { name } } }
              }
            }
          }
        }
        """
        response = httpx.post(
            "https://api.producthunt.com/v2/api/graphql",
            json={
                "query": query,
                "variables": {
                    "first": _int_config(source.query_config, "limit", default=30, maximum=100)
                },
            },
            timeout=self._timeout_seconds,
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return parse_product_hunt_posts(response.json(), since=since)


class HuggingFaceCollector(Collector):
    source_type = "hugging_face"

    def __init__(self, timeout_seconds: int = 20) -> None:
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        source: CollectableSourceDTO,
        *,
        since: datetime | None,
    ) -> list[RawCollectedItem]:
        headers = {"User-Agent": USER_AGENT}
        token = _env_token(source)
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = httpx.get(
            "https://huggingface.co/api/models",
            params={
                "search": _text_config(source.query_config, "query", default="llm"),
                "sort": _text_config(source.query_config, "sort", default="likes"),
                "direction": -1,
                "limit": _int_config(source.query_config, "limit", default=30, maximum=100),
            },
            timeout=self._timeout_seconds,
            headers=headers,
        )
        response.raise_for_status()
        return parse_hugging_face_models(response.json(), since=since)


def parse_hacker_news_hits(payload: dict[str, Any], *, since: datetime | None) -> list[RawCollectedItem]:
    items: list[RawCollectedItem] = []
    for hit in payload.get("hits", []):
        title = hit.get("title") or hit.get("story_title")
        object_id = str(hit.get("objectID") or "")
        if not title or not object_id:
            continue
        url = hit.get("url") or hit.get("story_url") or f"https://news.ycombinator.com/item?id={object_id}"
        published_at = _parse_datetime(hit.get("created_at"))
        if _is_before_since(published_at, since):
            continue
        items.append(
            RawCollectedItem(
                external_id=object_id,
                url=url,
                canonical_url=_canonical_url(url),
                title=title,
                author=hit.get("author"),
                published_at=published_at,
                raw_payload={
                    "description": hit.get("story_text") or hit.get("comment_text"),
                    "metrics": {"points": hit.get("points"), "comments": hit.get("num_comments")},
                    "source_payload": hit,
                },
            )
        )
    return items


def parse_github_repositories(
    payload: dict[str, Any], *, since: datetime | None
) -> list[RawCollectedItem]:
    items: list[RawCollectedItem] = []
    for repo in payload.get("items", []):
        full_name = repo.get("full_name")
        html_url = repo.get("html_url")
        if not full_name or not html_url:
            continue
        published_at = _parse_datetime(repo.get("pushed_at") or repo.get("updated_at"))
        if _is_before_since(published_at, since):
            continue
        description = repo.get("description")
        items.append(
            RawCollectedItem(
                external_id=str(repo.get("id") or full_name),
                url=html_url,
                canonical_url=_canonical_url(html_url),
                title=f"{full_name}: {description}" if description else full_name,
                author=(repo.get("owner") or {}).get("login"),
                published_at=published_at,
                raw_payload={
                    "description": description,
                    "metrics": {
                        "stars": repo.get("stargazers_count"),
                        "forks": repo.get("forks_count"),
                        "open_issues": repo.get("open_issues_count"),
                    },
                    "source_payload": repo,
                },
            )
        )
    return items


def parse_product_hunt_posts(
    payload: dict[str, Any], *, since: datetime | None
) -> list[RawCollectedItem]:
    posts = ((payload.get("data") or {}).get("posts") or {}).get("edges") or []
    items: list[RawCollectedItem] = []
    for edge in posts:
        node = edge.get("node") or {}
        post_id = node.get("id")
        title = node.get("name")
        url = node.get("url")
        if not post_id or not title or not url:
            continue
        published_at = _parse_datetime(node.get("createdAt"))
        if _is_before_since(published_at, since):
            continue
        topics = [
            (((topic_edge or {}).get("node") or {}).get("name"))
            for topic_edge in (((node.get("topics") or {}).get("edges")) or [])
        ]
        items.append(
            RawCollectedItem(
                external_id=str(post_id),
                url=url,
                canonical_url=_canonical_url(url),
                title=f"{title}: {node.get('tagline')}" if node.get("tagline") else title,
                author=(node.get("user") or {}).get("name"),
                published_at=published_at,
                raw_payload={
                    "description": node.get("tagline"),
                    "topics": [topic for topic in topics if topic],
                    "metrics": {
                        "votes": node.get("votesCount"),
                        "comments": node.get("commentsCount"),
                    },
                    "source_payload": node,
                },
            )
        )
    return items


def parse_hugging_face_models(
    payload: list[dict[str, Any]], *, since: datetime | None
) -> list[RawCollectedItem]:
    items: list[RawCollectedItem] = []
    for model in payload:
        model_id = model.get("modelId") or model.get("id")
        if not model_id:
            continue
        published_at = _parse_datetime(model.get("lastModified") or model.get("createdAt"))
        if _is_before_since(published_at, since):
            continue
        tags = model.get("tags") if isinstance(model.get("tags"), list) else []
        pipeline = model.get("pipeline_tag")
        description = " / ".join([value for value in [pipeline, ", ".join(tags[:5])] if value])
        url = f"https://huggingface.co/{model_id}"
        items.append(
            RawCollectedItem(
                external_id=str(model_id),
                url=url,
                canonical_url=_canonical_url(url),
                title=f"{model_id}: {description}" if description else str(model_id),
                author=str(model_id).split("/", 1)[0] if "/" in str(model_id) else None,
                published_at=published_at,
                raw_payload={
                    "description": description or None,
                    "tags": tags,
                    "metrics": {
                        "likes": model.get("likes"),
                        "downloads": model.get("downloads"),
                    },
                    "source_payload": model,
                },
            )
        )
    return items


def _text_config(config: dict[str, Any], key: str, *, default: str) -> str:
    value = config.get(key)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _int_config(config: dict[str, Any], key: str, *, default: int, maximum: int) -> int:
    try:
        value = int(config.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(1, min(value, maximum))


def _env_token(source: CollectableSourceDTO) -> str | None:
    if source.credential_secret:
        return source.credential_secret
    env_key = (
        source.credential_env_key
        or source.query_config.get("token_env")
        or source.query_config.get("api_key_env")
    )
    if not env_key:
        return None
    token = os.getenv(str(env_key).strip())
    return token or None


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _is_before_since(published_at: datetime | None, since: datetime | None) -> bool:
    if since is None or published_at is None:
        return False
    normalized_since = since if since.tzinfo is not None else since.replace(tzinfo=UTC)
    return published_at < normalized_since


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()
