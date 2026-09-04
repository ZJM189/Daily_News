from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.job_operations.dtos import SchedulerConfigDTO
from app.interfaces.scheduler import (
    _build_trigger,
    _scheduled_job_definitions,
    _scheduled_job_params,
)


def _config(
    *,
    job_type: str = "generate_digest",
    cron_expression: str = "0 8 * * *",
    timezone: str = "Asia/Shanghai",
    params: dict[str, object] | None = None,
) -> SchedulerConfigDTO:
    now = datetime(2026, 9, 4, 0, 0, tzinfo=UTC)
    return SchedulerConfigDTO(
        id=uuid4(),
        job_type=job_type,
        name="Daily AI Digest",
        cron_expression=cron_expression,
        timezone=timezone,
        enabled=True,
        params=params or {},
        created_by=None,
        updated_by=None,
        created_at=now,
        updated_at=now,
    )


def test_build_trigger_accepts_cron_and_timezone() -> None:
    trigger = _build_trigger(_config())

    assert str(trigger.fields[5]) == "8"
    assert str(trigger.fields[6]) == "0"
    assert str(trigger.timezone) == "Asia/Shanghai"


def test_build_trigger_rejects_invalid_timezone() -> None:
    with pytest.raises(ValueError, match="invalid scheduler timezone"):
        _build_trigger(_config(timezone="Invalid/Timezone"))


def test_scheduled_job_params_adds_digest_date_and_preserves_config() -> None:
    config = _config(params={"limit": 30, "exclude_recent_digest_days": 7})
    params = _scheduled_job_params(
        config,
        now=datetime(2026, 9, 4, 0, 0, tzinfo=UTC),
    )

    assert params == {
        "limit": 30,
        "exclude_recent_digest_days": 7,
        "digest_date": "2026-09-04",
        "timezone": "Asia/Shanghai",
    }


def test_scheduled_job_params_does_not_add_digest_fields_to_other_jobs() -> None:
    params = _scheduled_job_params(
        _config(job_type="collect"),
        now=datetime(2026, 9, 4, 8, 0, tzinfo=UTC),
    )

    assert params == {}


def test_scheduled_job_params_uses_configured_timezone_for_digest_date() -> None:
    params = _scheduled_job_params(
        _config(),
        now=datetime(2026, 9, 3, 16, 0, tzinfo=UTC),
    )

    assert params["digest_date"] == "2026-09-04"


def test_digest_schedule_expands_to_full_daily_pipeline() -> None:
    definitions = _scheduled_job_definitions(
        _config(
            params={
                "source_types": ["rss", "github"],
                "normalize_limit": 3000,
                "rank_limit": 2000,
                "topic_limit": 500,
                "summarize_limit": 80,
                "min_score": 65,
                "limit": 20,
            }
        ),
        now=datetime(2026, 9, 4, 0, 0, tzinfo=UTC),
    )

    assert [definition.job_type for definition in definitions] == [
        "collect",
        "normalize",
        "rank",
        "dedupe",
        "summarize",
        "generate_digest",
    ]
    assert definitions[0].params == {"source_types": ["rss", "github"]}
    assert definitions[1].params == {"limit": 3000}
    assert definitions[2].params == {"limit": 2000}
    assert definitions[3].params == {"limit": 500}
    assert definitions[4].params == {"limit": 80, "min_score": 65.0}
    assert definitions[5].params == {
        "limit": 20,
        "digest_date": "2026-09-04",
        "timezone": "Asia/Shanghai",
        "exclude_recent_digest_days": 3,
    }


def test_non_digest_schedule_creates_single_job_definition() -> None:
    definitions = _scheduled_job_definitions(
        _config(job_type="collect", params={"source_types": ["rss"]}),
    )

    assert len(definitions) == 1
    assert definitions[0].job_type == "collect"
    assert definitions[0].params == {"source_types": ["rss"]}
