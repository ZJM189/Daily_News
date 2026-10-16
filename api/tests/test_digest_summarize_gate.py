from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, create_engine
from sqlalchemy.orm import Session

from app.application.digest_publishing.service import digest_window
from app.infrastructure.digest_publishing.repositories import SqlAlchemyDigestPublishingRepository


@pytest.fixture
def summarize_jobs():
    engine = create_engine("sqlite://")
    # Only the columns used by the publication gate are needed for this SQL regression test.
    jobs = Table(
        "job_runs",
        MetaData(),
        Column("job_type", String),
        Column("status", String),
        Column("params", JSON),
        Column("created_at", DateTime(timezone=True)),
        Column("started_at", DateTime(timezone=True)),
    )
    jobs.metadata.create_all(engine)
    with Session(engine) as session:
        def add(status, *, batch=None, minute=0, job_type="summarize"):
            created_at = datetime(2026, 10, 16, tzinfo=UTC) + timedelta(minutes=minute)
            session.execute(jobs.insert().values(
                job_type=job_type,
                status=status,
                params={"pipeline_started_at": batch} if batch is not None else {},
                created_at=created_at,
                started_at=created_at,
            ))

        yield SqlAlchemyDigestPublishingRepository(session), add
    engine.dispose()


def _is_blocked(repo, *, batch=None, digest_date=date(2026, 10, 16)):
    start_at, end_at = digest_window(digest_date, "Asia/Shanghai")
    return repo.has_failed_summarize_job(
        start_at=start_at, end_at=end_at, pipeline_started_at=batch,
    )


def test_successful_rerun_ignores_earlier_failed_pipeline(summarize_jobs):
    repo, add = summarize_jobs
    add("failed", batch="scheduled")
    add("success", batch="manual", minute=48)

    assert not _is_blocked(repo, batch="manual")
    assert not _is_blocked(repo)
    assert _is_blocked(repo, batch="scheduled")


def test_other_pipeline_failure_does_not_block_successful_batch(summarize_jobs):
    repo, add = summarize_jobs
    add("success", batch="own")
    add("failed", batch="other", minute=10)

    assert not _is_blocked(repo, batch="own")
    assert _is_blocked(repo)


def test_successful_retry_with_same_batch_marker_clears_failure(summarize_jobs):
    repo, add = summarize_jobs
    add("failed", batch="own")
    add("success", batch="own", minute=10)

    assert not _is_blocked(repo, batch="own")


def test_latest_failure_with_same_batch_marker_still_blocks(summarize_jobs):
    repo, add = summarize_jobs
    add("success", batch="own")
    add("failed", batch="own", minute=10)

    assert _is_blocked(repo, batch="own")


def test_batch_matching_works_across_midnight(summarize_jobs):
    repo, add = summarize_jobs
    add("failed", batch="overnight", minute=-481)

    assert _is_blocked(repo, batch="overnight")
    assert not _is_blocked(repo)


def test_standalone_generation_uses_latest_legacy_summarize_attempt(summarize_jobs):
    repo, add = summarize_jobs
    add("failed")
    add("success", minute=10)
    add("failed", minute=20, job_type="collect")

    assert not _is_blocked(repo)


def test_missing_batch_does_not_fall_back_to_unrelated_failure(summarize_jobs):
    repo, add = summarize_jobs
    add("failed", batch="other")

    assert not _is_blocked(repo, batch="missing")


def test_standalone_generation_ignores_failures_outside_digest_day(summarize_jobs):
    repo, add = summarize_jobs
    add("failed", minute=-481)
    add("failed", minute=960)

    assert not _is_blocked(repo)
