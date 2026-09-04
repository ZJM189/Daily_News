from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.application.ingestion.dtos import ItemForRankingDTO
from app.application.ingestion.service import score_item


def test_score_item_combines_source_recency_keywords_and_completeness() -> None:
    now = datetime(2026, 9, 2, 8, 0, tzinfo=UTC)
    item = ItemForRankingDTO(
        id=uuid4(),
        source_id=uuid4(),
        source_type="rss",
        source_weight=80,
        title="OpenAI releases new GPT agent model",
        summary_original="A new AI model benchmark is available.",
        content_snippet=None,
        published_at=now - timedelta(hours=2),
        collected_at=now,
    )

    score, breakdown = score_item(item, now=now)

    assert score == 89
    assert breakdown["source_weight"] == 32
    assert breakdown["recency"] == 30
    assert breakdown["keyword"] == 15
    assert breakdown["completeness"] == 12
    assert breakdown["keyword_hits"] == ["agent", "ai", "benchmark", "gpt", "model", "openai"]


def test_score_item_clamps_score_to_100() -> None:
    now = datetime(2026, 9, 2, 8, 0, tzinfo=UTC)
    item = ItemForRankingDTO(
        id=uuid4(),
        source_id=uuid4(),
        source_type="rss",
        source_weight=100,
        title="OpenAI GPT Claude Gemini DeepSeek AI agent model benchmark research safety RAG",
        summary_original="LLM inference eval paper for artificial intelligence.",
        content_snippet="ChatGPT agents and models.",
        published_at=now,
        collected_at=now,
    )

    score, _breakdown = score_item(item, now=now)

    assert score == 100
