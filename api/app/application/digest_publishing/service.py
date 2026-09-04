from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.application.digest_publishing.dtos import (
    DigestCandidateDTO,
    DigestDetailDTO,
    GenerateDigestExecutionResult,
)
from app.application.digest_publishing.repositories import DigestPublishingRepository


class GenerateDigestJobExecutor:
    def __init__(self, repository: DigestPublishingRepository) -> None:
        self._repository = repository

    def run_next_generate_digest_job(self) -> GenerateDigestExecutionResult | None:
        job_run_id = self._repository.claim_next_generate_digest_job()
        if job_run_id is None:
            return None
        return self.run_generate_digest_job(job_run_id)

    def run_generate_digest_job(self, job_run_id: UUID) -> GenerateDigestExecutionResult:
        started_at = datetime.now(UTC)
        self._repository.mark_job_running(job_run_id, started_at)

        params = self._repository.get_job_params(job_run_id)
        digest_date = _date_or_today(params.get("digest_date"))
        timezone = _timezone_or_default(params.get("timezone"))
        limit = _positive_int(params.get("limit"), default=20, maximum=100)
        exclude_recent_digest_days = _non_negative_int(
            params.get("exclude_recent_digest_days"),
            default=3,
            maximum=30,
        )
        start_at, end_at = digest_window(digest_date, timezone)
        candidates = self._repository.list_digest_topic_candidates(
            digest_date=digest_date,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
            exclude_recent_digest_days=exclude_recent_digest_days,
        )

        generated_at = datetime.now(UTC)
        self._repository.create_published_digest(
            digest_date=digest_date,
            title=f"{digest_date.isoformat()} AI 热点简报",
            overview_zh=build_digest_overview(candidates),
            stats=build_digest_stats(candidates),
            job_run_id=job_run_id,
            candidates=candidates,
            generated_at=generated_at,
        )
        self._repository.mark_job_finished(
            job_run_id=job_run_id,
            status="success",
            total_count=len(candidates),
            success_count=len(candidates),
            failure_count=0,
            error_message=None,
            ended_at=datetime.now(UTC),
        )
        return GenerateDigestExecutionResult(
            job_run_id=job_run_id,
            total_count=len(candidates),
            success_count=len(candidates),
            failure_count=0,
        )


class DigestQueryService:
    def __init__(self, repository: DigestPublishingRepository) -> None:
        self._repository = repository

    def get_published_digest(
        self,
        *,
        digest_date: date,
        version: int | None,
    ) -> DigestDetailDTO | None:
        return self._repository.get_published_digest(
            digest_date=digest_date,
            version=version,
        )


def digest_window(digest_date: date, timezone: str) -> tuple[datetime, datetime]:
    tzinfo = ZoneInfo(timezone)
    start_at = datetime.combine(digest_date, time.min, tzinfo=tzinfo)
    end_at = start_at + timedelta(days=1)
    return start_at.astimezone(UTC), end_at.astimezone(UTC)


def build_digest_stats(candidates: list[DigestCandidateDTO]) -> dict[str, object]:
    return {
        "topic_count": len(candidates),
        "item_count": len(candidates),
        "source_count": sum(candidate.source_count for candidate in candidates),
    }


def build_digest_overview(candidates: list[DigestCandidateDTO]) -> str:
    if not candidates:
        return "本期没有符合条件的 AI 热点内容。"
    top_titles = "、".join(candidate.title for candidate in candidates[:3])
    return f"本期收录 {len(candidates)} 个 AI 热点专题，重点包括：{top_titles}。"


def _date_or_today(value: object) -> date:
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def _timezone_or_default(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "Asia/Shanghai"
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return "Asia/Shanghai"
    return value


def _positive_int(value: object, *, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < 1:
        return default
    return min(number, maximum)


def _non_negative_int(value: object, *, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < 0:
        return default
    return min(number, maximum)
