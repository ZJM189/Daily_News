from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.digest_publishing.dtos import DigestCandidateDTO
from app.application.digest_publishing.service import (
    GenerateDigestJobExecutor,
    build_digest_overview,
    build_digest_stats,
    digest_window,
)
from app.infrastructure.digest_publishing.repositories import (
    SqlAlchemyDigestPublishingRepository,
    select_evenly_by_source,
)
from app.infrastructure.models import CategoryCode, Item, Source, SourceStatus, SourceType, Topic


def test_digest_window_uses_explicit_timezone() -> None:
    start_at, end_at = digest_window(date(2026, 9, 2), "Asia/Shanghai")

    assert start_at == datetime(2026, 9, 1, 16, 0, tzinfo=UTC)
    assert end_at == datetime(2026, 9, 2, 16, 0, tzinfo=UTC)


def test_digest_overview_and_stats_from_topic_candidates() -> None:
    candidates = [
        _candidate(title="OpenAI 发布新模型", source_count=2),
        _candidate(title="开源社区更新推理框架", source_count=1),
    ]

    assert build_digest_stats(candidates) == {
        "topic_count": 2,
        "item_count": 2,
        "source_count": 3,
    }
    assert build_digest_overview(candidates) == (
        "本期收录 2 个 AI 热点专题，重点包括：OpenAI 发布新模型、开源社区更新推理框架。"
    )


def test_digest_overview_handles_empty_candidates() -> None:
    assert build_digest_overview([]) == "本期没有符合条件的 AI 热点内容。"


def test_topic_candidate_uses_primary_item_summary_as_fallback() -> None:
    primary_item_id = uuid4()
    primary_source_id = uuid4()
    topic = Topic(
        id=uuid4(),
        title="Shubhamsaboo/awesome-llm-apps",
        normalized_key="title:awesome-llm-apps",
        category=CategoryCode.OPEN_SOURCE,
        tags=["agent"],
        score=Decimal("80.50"),
        source_count=1,
        primary_item_id=primary_item_id,
        first_seen_at=datetime(2026, 9, 3, tzinfo=UTC),
        last_seen_at=datetime(2026, 9, 3, tzinfo=UTC),
    )
    primary_item = Item(
        id=primary_item_id,
        source_id=primary_source_id,
        title="Shubhamsaboo/awesome-llm-apps",
        normalized_title="shubhamsaboo/awesome-llm-apps",
        title_hash="hash",
        url="https://github.com/Shubhamsaboo/awesome-llm-apps",
        canonical_url="https://github.com/Shubhamsaboo/awesome-llm-apps",
        category=CategoryCode.OPEN_SOURCE,
        summary_zh="这是 primary item 的中文摘要。",
        importance_zh="这是 primary item 的重要性说明。",
    )
    primary_source = Source(
        id=primary_source_id,
        name="GitHub AI Trending",
        type=SourceType.GITHUB,
        status=SourceStatus.ENABLED,
    )

    candidate = SqlAlchemyDigestPublishingRepository(None)._topic_to_candidate(
        topic,
        primary_item,
        primary_source,
    )

    assert candidate.summary_zh == "这是 primary item 的中文摘要。"
    assert candidate.importance_zh == "这是 primary item 的重要性说明。"
    assert candidate.primary_source_type == "github"
    assert candidate.primary_source_name == "GitHub AI Trending"
    assert candidate.primary_url == "https://github.com/Shubhamsaboo/awesome-llm-apps"
    assert candidate.canonical_url == "https://github.com/Shubhamsaboo/awesome-llm-apps"


def test_select_evenly_by_source_round_robins_by_source() -> None:
    source_a = uuid4()
    source_b = uuid4()
    source_c = uuid4()
    candidates = [
        (_candidate(title="A1", score="99"), source_a, datetime(2026, 9, 3, 8, 0, tzinfo=UTC)),
        (_candidate(title="A2", score="96"), source_a, datetime(2026, 9, 3, 7, 0, tzinfo=UTC)),
        (_candidate(title="B1", score="98"), source_b, datetime(2026, 9, 3, 8, 0, tzinfo=UTC)),
        (_candidate(title="B2", score="95"), source_b, datetime(2026, 9, 3, 7, 0, tzinfo=UTC)),
        (_candidate(title="C1", score="97"), source_c, datetime(2026, 9, 3, 8, 0, tzinfo=UTC)),
    ]

    selected = select_evenly_by_source(candidates, limit=5)

    assert [candidate.title for candidate in selected] == ["A1", "B1", "C1", "A2", "B2"]


def test_generate_digest_job_defaults_to_recent_digest_exclusion() -> None:
    repo = _FakeDigestRepository(
        params={"digest_date": "2026-09-03", "timezone": "Asia/Shanghai", "limit": 5},
        candidates=[_candidate(title="OpenAI 发布新模型", source_count=2)],
    )

    result = GenerateDigestJobExecutor(repo).run_generate_digest_job(uuid4())

    assert result.total_count == 1
    assert repo.list_args["exclude_recent_digest_days"] == 3
    assert repo.list_args["digest_date"].isoformat() == "2026-09-03"
    assert repo.list_args["start_at"] == datetime(2026, 9, 2, 16, 0, tzinfo=UTC)
    assert repo.list_args["end_at"] == datetime(2026, 9, 3, 16, 0, tzinfo=UTC)


def test_generate_digest_job_accepts_recent_digest_exclusion_override() -> None:
    repo = _FakeDigestRepository(
        params={
            "digest_date": "2026-09-03",
            "timezone": "Asia/Shanghai",
            "limit": 5,
            "exclude_recent_digest_days": 7,
        },
        candidates=[_candidate(title="OpenAI 发布新模型", source_count=2)],
    )

    GenerateDigestJobExecutor(repo).run_generate_digest_job(uuid4())

    assert repo.list_args["exclude_recent_digest_days"] == 7


def _candidate(
    *,
    title: str,
    source_count: int = 1,
    score: str = "80",
) -> DigestCandidateDTO:
    return DigestCandidateDTO(
        topic_id=uuid4(),
        title=title,
        summary_zh=None,
        importance_zh=None,
        category="other",
        score=Decimal(score),
        source_count=source_count,
        primary_item_id=uuid4(),
    )


class _FakeDigestRepository:
    def __init__(self, *, params: dict[str, object], candidates: list[DigestCandidateDTO]) -> None:
        self.params = params
        self.candidates = candidates
        self.list_args: dict[str, object] = {}

    def mark_job_running(self, job_run_id, started_at: datetime) -> None:
        pass

    def get_job_params(self, job_run_id) -> dict[str, object]:
        return self.params

    def list_digest_topic_candidates(
        self,
        *,
        digest_date,
        start_at,
        end_at,
        limit,
        exclude_recent_digest_days,
    ):
        self.list_args = {
            "digest_date": digest_date,
            "start_at": start_at,
            "end_at": end_at,
            "limit": limit,
            "exclude_recent_digest_days": exclude_recent_digest_days,
        }
        return self.candidates[:limit]

    def create_published_digest(
        self,
        *,
        digest_date,
        title,
        overview_zh,
        stats,
        job_run_id,
        candidates,
        generated_at,
    ):
        self.created_digest = {
            "digest_date": digest_date,
            "title": title,
            "overview_zh": overview_zh,
            "stats": stats,
            "job_run_id": job_run_id,
            "candidates": candidates,
            "generated_at": generated_at,
        }

    def mark_job_finished(
        self,
        *,
        job_run_id,
        status,
        total_count,
        success_count,
        failure_count,
        error_message,
        ended_at,
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
