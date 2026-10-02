from datetime import UTC, datetime
from uuid import uuid4

import httpx

import app.infrastructure.typesafe_jev.client as jev_client_module
from app.application.decision.dtos import (
    ItemDecisionDTO,
    ItemDecisionEvaluationDTO,
    StructuredAnswerDTO,
    StructuredDecisionDTO,
)
from app.application.decision.item import ItemDecisionService
from app.application.decision.scoring import compose_item_score
from app.application.ingestion.dtos import ItemForRankingDTO
from app.infrastructure.typesafe_jev.client import (
    JevClientConfig,
    TypeSafeJevClient,
    _extract_answers,
)


class _FakeDecisionClient:
    def __init__(self, result: StructuredDecisionDTO) -> None:
        self.result = result
        self.states: list[dict[str, object]] = []

    def evaluate(self, *, state, questions):
        self.states.append(state)
        return self.result


def test_item_decision_service_maps_structured_answers() -> None:
    client = _FakeDecisionClient(
        StructuredDecisionDTO(
            model="jev-test",
            answers={
                "is_ai_related": StructuredAnswerDTO("noul", 0.95, 0.9, 0.95),
                "prompt_injection": StructuredAnswerDTO("noul", 0.01, 0.9, 0.01),
                "category": StructuredAnswerDTO("choice", "open_source", 0.9),
                "importance": StructuredAnswerDTO("score", "非常重要", 0.8),
                "quality": StructuredAnswerDTO("score", "高", 0.8),
            },
            latency_ms=42,
        )
    )
    service = ItemDecisionService(client)

    result = service.evaluate(_item())

    assert result.status == "success"
    assert result.decision is not None
    assert result.decision.category == "open_source"
    assert result.decision.is_ai_related == 0.95
    assert result.decision.importance_score == 100
    assert result.decision.quality_score == 100
    assert client.states[0]["title"].startswith("Open-source")


def test_compose_item_score_falls_back_when_jev_fails() -> None:
    score, breakdown = compose_item_score(
        rule_score=82,
        rule_breakdown={"recency": 30},
        evaluation=ItemDecisionEvaluationDTO(
            decision=None,
            status="failed",
            error_message="timeout",
        ),
        jev_weight=0.3,
    )

    assert score == 82
    assert breakdown["jev"] == {"status": "failed", "error": "timeout"}
    assert breakdown["final"] == 82


def test_compose_item_score_blocks_prompt_injection() -> None:
    decision = ItemDecisionDTO(
        is_ai_related=0.9,
        prompt_injection=0.8,
        importance_score=80,
        quality_score=80,
        category="other",
        confidence=0.9,
        model="jev-test",
    )

    score, breakdown = compose_item_score(
        rule_score=90,
        rule_breakdown={},
        evaluation=ItemDecisionEvaluationDTO(decision=decision, status="success"),
        jev_weight=0.3,
    )

    assert score == 0
    assert breakdown["jev"]["blocked"] is True


def test_extract_answers_accepts_system_one_answer_payload() -> None:
    answers = _extract_answers(
        {
            "answers": {
                "allowed": {"type": "noul", "noul": 0.91, "confidence": 0.8},
                "intent": {"type": "choice", "choice": "library_search", "confidence": 0.9},
            }
        },
        questions={
            "allowed": {"type": "noul"},
            "intent": {"type": "choice"},
        },
    )

    assert answers["allowed"].probability == 0.91
    assert answers["intent"].value == "library_search"


def test_jev_endpoint_builder_supports_full_endpoint() -> None:
    client = TypeSafeJevClient(
        JevClientConfig(
            base_url="https://api.typesafe.ai/v1/systemone",
            api_key="test",
            model="jev-test",
        )
    )

    assert client._config.base_url.endswith("/v1/systemone")


def test_jev_client_retries_rate_limit(monkeypatch) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "model": "jev-test",
                "answers": {
                    "related": {
                        "type": "noul",
                        "noul": 0.9,
                        "confidence": 0.8,
                    }
                },
            },
            request=request,
        )

    monkeypatch.setattr(jev_client_module, "_sleep_before_retry", lambda **_: None)
    client = TypeSafeJevClient(
        JevClientConfig(
            base_url="https://api.typesafe.ai",
            api_key="test",
            model="jev-test",
            retry_count=1,
        ),
        transport=httpx.MockTransport(handler),
    )

    result = client.evaluate(
        state={"text": "AI"},
        questions={"related": {"type": "noul"}},
    )

    assert calls == 2
    assert result.answers["related"].probability == 0.9


def _item() -> ItemForRankingDTO:
    now = datetime.now(UTC)
    return ItemForRankingDTO(
        id=uuid4(),
        source_id=uuid4(),
        source_type="rss",
        source_weight=80,
        title="Open-source AI agent framework",
        summary_original="A new open-source agent framework.",
        content_snippet="Tool calling and workflow orchestration.",
        tags=["agent"],
        published_at=now,
        collected_at=now,
    )
