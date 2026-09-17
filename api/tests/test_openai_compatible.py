from typing import Self
from uuid import uuid4

import httpx

from app.application.ingestion.dtos import LLMRuntimeProviderDTO
from app.infrastructure.ingestion import openai_compatible


def test_post_chat_completion_retries_rate_limit(monkeypatch) -> None:
    calls: list[str] = []
    sleeps: list[float] = []

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            assert timeout == 30

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]):
            calls.append(url)
            request = httpx.Request("POST", url)
            if len(calls) == 1:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "0"},
                    request=request,
                    json={"error": {"message": "too many requests"}},
                )
            return httpx.Response(
                200,
                request=request,
                json={"choices": [{"message": {"content": "{}"}}]},
            )

    monkeypatch.setattr(openai_compatible.httpx, "Client", FakeClient)
    monkeypatch.setattr(openai_compatible.time, "sleep", sleeps.append)
    provider = LLMRuntimeProviderDTO(
        id=uuid4(),
        name="test",
        base_url="https://example.test/v1",
        model="test-model",
        api_key="token",
        timeout_seconds=30,
        retry_count=1,
    )

    payload = openai_compatible._post_chat_completion(
        provider=provider,
        headers={"Content-Type": "application/json"},
        payload={"model": "test-model", "messages": []},
    )

    assert payload == {"choices": [{"message": {"content": "{}"}}]}
    assert calls == [
        "https://example.test/v1/chat/completions",
        "https://example.test/v1/chat/completions",
    ]
    assert sleeps == [0.0]


def test_post_chat_completion_uses_backoff_jitter_without_retry_after(monkeypatch) -> None:
    calls: list[str] = []
    sleeps: list[float] = []

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            assert timeout == 30

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]):
            calls.append(url)
            request = httpx.Request("POST", url)
            if len(calls) == 1:
                return httpx.Response(
                    429,
                    request=request,
                    json={"error": {"message": "too many requests"}},
                )
            return httpx.Response(
                200,
                request=request,
                json={"choices": [{"message": {"content": "{}"}}]},
            )

    monkeypatch.setattr(openai_compatible.httpx, "Client", FakeClient)
    monkeypatch.setattr(openai_compatible.random, "uniform", lambda start, end: 0.25)
    monkeypatch.setattr(openai_compatible.time, "sleep", sleeps.append)
    provider = LLMRuntimeProviderDTO(
        id=uuid4(),
        name="test",
        base_url="https://example.test/v1",
        model="test-model",
        api_key="token",
        timeout_seconds=30,
        retry_count=1,
    )

    openai_compatible._post_chat_completion(
        provider=provider,
        headers={"Content-Type": "application/json"},
        payload={"model": "test-model", "messages": []},
    )

    assert sleeps == [1.25]
