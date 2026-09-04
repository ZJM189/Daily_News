from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.application.ingestion.dtos import (
    ItemForSummarizationDTO,
    ItemSummaryDTO,
    LLMRuntimeProviderDTO,
)
from app.application.ingestion.summarization import (
    ITEM_SUMMARY_PROMPT_VERSION,
    SummarizeJobExecutor,
    SummarySchemaError,
    validate_item_summary,
)
from app.infrastructure.ingestion.repositories import select_balanced_items_by_source


def test_validate_item_summary_requires_chinese_summary_fields_and_ignores_category() -> None:
    payload = {
        "summary_zh": "OpenAI 发布了新的模型能力。",
        "importance_zh": "这会影响企业采用 AI 的方式。",
        "category": "model_company",
        "tags": ["OpenAI", "模型", "AI", "AI"],
        "confidence": 1.5,
    }

    summary = validate_item_summary(payload)

    assert summary.summary_zh == "OpenAI 发布了新的模型能力。"
    assert summary.importance_zh == "这会影响企业采用 AI 的方式。"
    assert summary.category == "other"
    assert summary.tags == ["OpenAI", "模型", "AI"]
    assert summary.confidence == 1


def test_validate_item_summary_rejects_missing_required_fields() -> None:
    try:
        validate_item_summary({"summary_zh": ""})
    except SummarySchemaError as exc:
        assert "summary_zh" in str(exc)
    else:
        raise AssertionError("expected SummarySchemaError")


def test_summarize_job_fails_without_default_provider() -> None:
    repo = _FakeSummarizeRepository(provider=None, items=[])
    result = SummarizeJobExecutor(repo, _FakeSummarizationClient()).run_summarize_job(uuid4())

    assert result.total_count == 0
    assert result.success_count == 0
    assert result.failure_count == 1
    assert repo.finished_status == "failed"
    assert repo.finished_error == "no enabled default llm provider configured"


def test_summarize_job_marks_item_summarized_and_logs_call() -> None:
    provider = _provider()
    item = _item()
    repo = _FakeSummarizeRepository(provider=provider, items=[item])

    result = SummarizeJobExecutor(repo, _FakeSummarizationClient()).run_summarize_job(uuid4())

    assert result.total_count == 1
    assert result.success_count == 1
    assert result.failure_count == 0
    assert repo.finished_status == "success"
    assert repo.summarized_item_ids == [item.id]
    assert repo.prompt_versions == [ITEM_SUMMARY_PROMPT_VERSION]
    assert repo.llm_logs == [("item", item.id, "success")]


def test_select_balanced_items_by_source_spreads_sources_before_filling() -> None:
    source_a = uuid4()
    source_b = uuid4()
    source_c = uuid4()
    items = [
        _item_with_source(
            source_id=source_a,
            title="A-99",
            score="99",
            published_at=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        ),
        _item_with_source(
            source_id=source_a,
            title="A-98",
            score="98",
            published_at=datetime(2026, 9, 2, 7, 0, tzinfo=UTC),
        ),
        _item_with_source(
            source_id=source_b,
            title="B-97",
            score="97",
            published_at=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        ),
        _item_with_source(
            source_id=source_c,
            title="C-96",
            score="96",
            published_at=datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
        ),
        _item_with_source(
            source_id=source_c,
            title="C-95",
            score="95",
            published_at=datetime(2026, 9, 2, 7, 0, tzinfo=UTC),
        ),
    ]

    selected = select_balanced_items_by_source(items, limit=4, max_per_source=2)

    assert [item.title for item in selected] == ["A-99", "B-97", "C-96", "A-98"]
    assert len({item.source_id for item in selected}) == 3


def _provider() -> LLMRuntimeProviderDTO:
    return LLMRuntimeProviderDTO(
        id=uuid4(),
        name="test",
        base_url="https://example.com/v1",
        model="test-model",
        api_key="sk-test",
        timeout_seconds=30,
        retry_count=0,
    )


def _item() -> ItemForSummarizationDTO:
    return _item_with_source()


def _item_with_source(
    *,
    source_id: UUID | None = None,
    title: str = "OpenAI releases a new model",
    score: str = "85.5",
    published_at: datetime | None = None,
) -> ItemForSummarizationDTO:
    return ItemForSummarizationDTO(
        id=uuid4(),
        source_id=source_id or uuid4(),
        title=title,
        url="https://example.com/news",
        summary_original="OpenAI released a new AI model.",
        content_snippet=None,
        score=Decimal(score),
        published_at=published_at or datetime(2026, 9, 2, 8, 0, tzinfo=UTC),
    )


class _FakeSummarizationClient:
    def summarize_item(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        item: ItemForSummarizationDTO,
    ) -> ItemSummaryDTO:
        return ItemSummaryDTO(
            summary_zh=f"{item.title} 的中文摘要",
            importance_zh="这是一条重要 AI 新闻。",
            category="model_company",
            tags=["OpenAI", "AI"],
            confidence=0.9,
            input_tokens=100,
            output_tokens=50,
            latency_ms=123,
        )


class _FakeSummarizeRepository:
    def __init__(
        self,
        *,
        provider: LLMRuntimeProviderDTO | None,
        items: list[ItemForSummarizationDTO],
    ) -> None:
        self.provider = provider
        self.items = items
        self.finished_status: str | None = None
        self.finished_error: str | None = None
        self.summarized_item_ids: list[UUID] = []
        self.prompt_versions: list[str] = []
        self.llm_logs: list[tuple[str, UUID, str]] = []

    def mark_job_running(self, job_run_id: UUID, started_at: datetime) -> None:
        pass

    def get_job_params(self, job_run_id: UUID) -> dict[str, object]:
        return {"limit": 10, "min_score": 60}

    def get_default_llm_provider(self) -> LLMRuntimeProviderDTO | None:
        return self.provider

    def list_items_for_summarization(
        self,
        *,
        source_id: UUID | None,
        limit: int,
        min_score: float,
    ) -> list[ItemForSummarizationDTO]:
        return self.items[:limit]

    def mark_item_summarized(
        self,
        *,
        item_id: UUID,
        provider: LLMRuntimeProviderDTO,
        summary: ItemSummaryDTO,
        prompt_version: str,
    ) -> None:
        self.summarized_item_ids.append(item_id)
        self.prompt_versions.append(prompt_version)

    def mark_item_summary_failed(self, *, item_id: UUID, error: str) -> None:
        pass

    def log_llm_call(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        object_type: str,
        object_id: UUID,
        status: str,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: int | None,
        error_message: str | None,
    ) -> None:
        self.llm_logs.append((object_type, object_id, status))

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
        self.finished_status = status
        self.finished_error = error_message
