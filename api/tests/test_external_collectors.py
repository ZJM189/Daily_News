from datetime import datetime
from uuid import uuid4

import httpx

from app.application.ingestion.dtos import CollectableSourceDTO
from app.infrastructure.ingestion.external_collectors import (
    GitHubCollector,
    parse_github_repositories,
    parse_hacker_news_hits,
    parse_hugging_face_models,
    parse_product_hunt_posts,
)


def test_parse_hacker_news_hits_uses_hn_permalink_when_url_missing() -> None:
    payload = {
        "hits": [
            {
                "objectID": "123",
                "title": "AI launch",
                "author": "pg",
                "created_at": "2026-09-02T08:00:00Z",
                "points": 120,
                "num_comments": 34,
            }
        ]
    }

    items = parse_hacker_news_hits(payload, since=None)

    assert len(items) == 1
    assert items[0].external_id == "123"
    assert items[0].url == "https://news.ycombinator.com/item?id=123"
    assert items[0].raw_payload["metrics"]["points"] == 120


def test_parse_github_repositories_maps_description_and_metrics() -> None:
    payload = {
        "items": [
            {
                "id": 1,
                "full_name": "owner/project",
                "html_url": "https://github.com/owner/project#readme",
                "description": "AI coding agent",
                "owner": {"login": "owner"},
                "pushed_at": "2026-09-02T08:00:00Z",
                "stargazers_count": 1000,
                "forks_count": 40,
                "open_issues_count": 5,
            }
        ]
    }

    items = parse_github_repositories(payload, since=None)

    assert len(items) == 1
    assert items[0].title == "owner/project: AI coding agent"
    assert items[0].canonical_url == "https://github.com/owner/project"
    assert items[0].raw_payload["description"] == "AI coding agent"
    assert items[0].raw_payload["metrics"]["stars"] == 1000


def test_github_collector_uses_database_credential_as_bearer_token(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_get(url, *, params, headers, timeout):
        captured.update({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return httpx.Response(
            200,
            json={"items": []},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    source = CollectableSourceDTO(
        id=uuid4(),
        name="GitHub",
        type="github",
        status="enabled",
        url="https://api.github.com/search/repositories",
        query_config={"query": "AI", "sort": "updated", "limit": 10},
        credential_secret="github-token",
        credential_env_key=None,
        weight=50,
        language="en",
    )

    GitHubCollector().collect(source, since=None)

    assert captured["headers"]["Authorization"] == "Bearer github-token"


def test_parse_product_hunt_posts_filters_by_since() -> None:
    payload = {
        "data": {
            "posts": {
                "edges": [
                    {
                        "node": {
                            "id": "post-1",
                            "name": "AI Tool",
                            "tagline": "Summarize daily AI news",
                            "url": "https://www.producthunt.com/posts/ai-tool",
                            "createdAt": "2026-09-01T08:00:00Z",
                            "votesCount": 10,
                            "commentsCount": 2,
                            "user": {"name": "Maker"},
                            "topics": {"edges": [{"node": {"name": "Artificial Intelligence"}}]},
                        }
                    }
                ]
            }
        }
    }

    items = parse_product_hunt_posts(
        payload,
        since=datetime.fromisoformat("2026-09-02T00:00:00+00:00"),
    )

    assert items == []


def test_parse_hugging_face_models_maps_model_cards() -> None:
    payload = [
        {
            "modelId": "org/model",
            "pipeline_tag": "text-generation",
            "tags": ["transformers", "llm"],
            "lastModified": "2026-09-02T08:00:00Z",
            "likes": 500,
            "downloads": 12000,
        }
    ]

    items = parse_hugging_face_models(payload, since=None)

    assert len(items) == 1
    assert items[0].url == "https://huggingface.co/org/model"
    assert items[0].author == "org"
    assert items[0].raw_payload["metrics"]["downloads"] == 12000
