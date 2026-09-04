from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.application.ingestion.dtos import ItemForTopicAggregationDTO, LLMRuntimeProviderDTO
from app.application.ingestion.topic_aggregation import (
    TopicAggregationJobExecutor,
    aggregate_topic_groups,
    aggregate_topic_groups_with_llm,
    build_topic_key,
)
from app.infrastructure.ingestion.openai_compatible import (
    parse_topic_aggregation_payload,
    parse_topic_consolidation_payload,
)
from app.infrastructure.ingestion.repositories import select_balanced_items_by_source


def _item(
    *,
    title: str,
    source_id,
    score: str,
    canonical_url: str | None = None,
    published_at: datetime | None = None,
) -> ItemForTopicAggregationDTO:
    return ItemForTopicAggregationDTO(
        id=uuid4(),
        source_id=source_id,
        title=title,
        normalized_title=title.lower(),
        url=canonical_url or "https://example.com/story",
        canonical_url=canonical_url,
        summary_original=None,
        content_snippet=None,
        summary_zh=f"{title} 的中文摘要",
        importance_zh=f"{title} 的重要性说明",
        category="other",
        tags=["ai"],
        score=Decimal(score),
        published_at=published_at,
        collected_at=published_at or datetime.now(UTC),
    )


def test_build_topic_key_normalizes_title() -> None:
    source_id = uuid4()
    first = _item(
        title="A title",
        source_id=source_id,
        score="80",
        canonical_url="HTTPS://Example.com/story/",
    )
    second = _item(
        title="A different title",
        source_id=source_id,
        score="70",
        canonical_url="https://example.com/story",
    )

    assert build_topic_key(first) == "title:a title"
    assert build_topic_key(second) == "title:a different title"


def test_aggregate_topic_groups_selects_primary_and_rewards_diversity() -> None:
    now = datetime(2026, 9, 2, 8, 0, tzinfo=UTC)
    first = _item(
        title="OpenAI releases a new model",
        source_id=uuid4(),
        score="80",
        published_at=now,
    )
    second = _item(
        title="OpenAI releases a new model",
        source_id=uuid4(),
        score="75",
        published_at=now - timedelta(hours=1),
    )

    groups = aggregate_topic_groups([second, first])

    assert len(groups) == 1
    group = groups[0]
    assert group.primary_item_id == first.id
    assert group.item_ids == [first.id, second.id]
    assert group.source_count == 2
    assert group.score == 84
    assert group.first_seen_at == second.published_at
    assert group.last_seen_at == first.published_at


def test_aggregate_topic_groups_keeps_different_titles_separate_without_url() -> None:
    items = [
        _item(title="OpenAI releases a new model", source_id=uuid4(), score="80"),
        _item(title="Anthropic releases a new model", source_id=uuid4(), score="80"),
    ]

    groups = aggregate_topic_groups(items)

    assert len(groups) == 2


def test_aggregate_topic_groups_merges_similar_title_keyword_combinations() -> None:
    source_id = uuid4()
    items = [
        _item(
            title="OpenAI releases a new model",
            source_id=source_id,
            score="80",
            canonical_url="https://example.com/one",
        ),
        _item(
            title="OpenAI releases model",
            source_id=uuid4(),
            score="75",
            canonical_url="https://example.com/two",
        ),
    ]

    groups = aggregate_topic_groups(items)

    assert len(groups) == 1
    assert len(groups[0].item_ids) == 2


def test_parse_topic_aggregation_payload_uses_llm_groups_and_singletons() -> None:
    first = _item(title="OpenAI releases GPT-5", source_id=uuid4(), score="90")
    second = _item(title="GPT-5 system card published", source_id=uuid4(), score="85")
    third = _item(title="Dify releases workflow update", source_id=uuid4(), score="75")

    groups = parse_topic_aggregation_payload(
        {
            "topics": [
                {
                    "title_zh": "OpenAI 发布 GPT-5 及系统卡",
                    "summary_zh": "OpenAI 发布 GPT-5，并同步公开系统卡。",
                    "importance_zh": "该发布会影响模型能力评估和安全治理。",
                    "category": "model_company",
                    "tags": ["OpenAI", "GPT-5"],
                    "confidence": 0.9,
                    "item_ids": [str(first.id), str(second.id), "not-exists"],
                }
            ]
        },
        items=[first, second, third],
    )

    assert len(groups) == 2
    merged = groups[0]
    assert merged.title == "OpenAI 发布 GPT-5 及系统卡"
    assert merged.item_ids == [first.id, second.id]
    assert merged.category == "other"
    assert merged.summary_zh == "OpenAI 发布 GPT-5，并同步公开系统卡。"
    assert merged.importance_zh == "该发布会影响模型能力评估和安全治理。"
    assert merged.confidence == 0.9
    singleton = groups[1]
    assert singleton.item_ids == [third.id]


def test_parse_topic_consolidation_payload_merges_cross_batch_groups() -> None:
    first = _item(title="OpenAI releases GPT-5", source_id=uuid4(), score="90")
    second = _item(title="GPT-5 system card published", source_id=uuid4(), score="85")
    third = _item(title="Dify releases workflow update", source_id=uuid4(), score="75")
    input_groups = [
        aggregate_topic_groups([first])[0],
        aggregate_topic_groups([second])[0],
        aggregate_topic_groups([third])[0],
    ]

    groups = parse_topic_consolidation_payload(
        {
            "topics": [
                {
                    "title_zh": "OpenAI 发布 GPT-5 及系统卡",
                    "summary_zh": "OpenAI 发布 GPT-5，并同步公开系统卡。",
                    "importance_zh": "该专题影响模型能力评估和安全治理。",
                    "tags": ["OpenAI", "GPT-5"],
                    "confidence": 0.8,
                    "group_ids": ["g1", "g2", "not-exists"],
                }
            ]
        },
        groups=input_groups,
    )

    assert len(groups) == 2
    merged = groups[0]
    assert merged.title == "OpenAI 发布 GPT-5 及系统卡"
    assert merged.item_ids == [first.id, second.id]
    assert merged.primary_item_id == first.id
    assert merged.summary_zh == "OpenAI 发布 GPT-5，并同步公开系统卡。"
    assert merged.importance_zh == "该专题影响模型能力评估和安全治理。"
    assert merged.confidence == 0.8
    assert "OpenAI" in merged.tags
    assert groups[1].item_ids == [third.id]


def test_aggregate_topic_groups_with_llm_falls_back_per_failed_batch() -> None:
    items = [
        _item(title="OpenAI releases GPT-5", source_id=uuid4(), score="90"),
        _item(title="OpenAI publishes GPT-5 system card", source_id=uuid4(), score="85"),
        _item(title="Dify releases workflow update", source_id=uuid4(), score="75"),
    ]
    provider = LLMRuntimeProviderDTO(
        id=uuid4(),
        name="test-provider",
        base_url="https://example.com/v1",
        model="test-model",
        api_key=None,
        timeout_seconds=1,
        retry_count=0,
    )
    client = _FailingSecondBatchTopicClient()

    groups, errors = aggregate_topic_groups_with_llm(
        provider=provider,
        client=client,
        items=items,
        batch_size=2,
    )

    assert client.calls == 2
    assert len(errors) == 1
    assert "batch 2 failed" in errors[0]
    assert sum(len(group.item_ids) for group in groups) == 3


def test_topic_aggregation_job_marks_success_when_llm_fallback_upserts() -> None:
    items = [
        _item(title="OpenAI releases GPT-5", source_id=uuid4(), score="90"),
        _item(title="OpenAI publishes GPT-5 system card", source_id=uuid4(), score="85"),
        _item(title="Dify releases workflow update", source_id=uuid4(), score="75"),
    ]
    provider = LLMRuntimeProviderDTO(
        id=uuid4(),
        name="test-provider",
        base_url="https://example.com/v1",
        model="test-model",
        api_key=None,
        timeout_seconds=1,
        retry_count=0,
    )
    repo = _TopicAggregationRepository(items=items, provider=provider)
    executor = TopicAggregationJobExecutor(repo, _FailingSecondBatchTopicClient())

    result = executor.run_topic_aggregation_job(repo.job_run_id)

    assert result.success_count == 3
    assert result.failure_count == 0
    assert len(repo.upserted_group_keys) == 3
    assert repo.finished["status"] == "success"
    assert repo.finished["error_message"] is None


def test_select_balanced_items_by_source_works_for_topic_items() -> None:
    source_a = uuid4()
    source_b = uuid4()
    source_c = uuid4()
    items = [
        _item(title="A-99", source_id=source_a, score="99"),
        _item(title="A-98", source_id=source_a, score="98"),
        _item(title="B-97", source_id=source_b, score="97"),
        _item(title="C-96", source_id=source_c, score="96"),
    ]

    selected = select_balanced_items_by_source(items, limit=4)

    assert [item.title for item in selected] == ["A-99", "B-97", "C-96", "A-98"]


class _FailingSecondBatchTopicClient:
    def __init__(self) -> None:
        self.calls = 0

    def aggregate_topics(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        items: list[ItemForTopicAggregationDTO],
    ):
        self.calls += 1
        if self.calls == 2:
            raise TimeoutError("timeout")
        return aggregate_topic_groups(items)

    def consolidate_topic_groups(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        groups,
    ):
        return groups


class _TopicAggregationRepository:
    def __init__(
        self,
        *,
        items: list[ItemForTopicAggregationDTO],
        provider: LLMRuntimeProviderDTO,
    ) -> None:
        self.job_run_id = uuid4()
        self.items = items
        self.provider = provider
        self.upserted_group_keys: list[str] = []
        self.finished: dict[str, object] = {}

    def claim_next_topic_aggregation_job(self) -> UUID | None:
        return self.job_run_id

    def mark_job_running(self, job_run_id: UUID, started_at: datetime) -> None:
        pass

    def get_job_params(self, job_run_id: UUID) -> dict[str, object]:
        return {"limit": 10, "min_score": 60, "batch_size": 2}

    def get_default_llm_provider(self) -> LLMRuntimeProviderDTO | None:
        return self.provider

    def list_items_for_topic_aggregation(
        self,
        *,
        source_id: UUID | None,
        limit: int,
        min_score: float,
    ) -> list[ItemForTopicAggregationDTO]:
        return self.items[:limit]

    def upsert_topic_group(self, group) -> None:
        self.upserted_group_keys.append(group.normalized_key)

    def mark_job_finished(
        self,
        *,
        job_run_id: UUID,
        status: str,
        total_count: int,
        success_count: int,
        failure_count: int,
        error_message: str | None,
        ended_at: datetime,
    ) -> None:
        self.finished = {
            "job_run_id": job_run_id,
            "status": status,
            "total_count": total_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "error_message": error_message,
            "ended_at": ended_at,
        }
