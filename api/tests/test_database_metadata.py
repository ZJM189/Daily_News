from app.infrastructure import models  # noqa: F401
from app.infrastructure.persistence import Base


def test_initial_schema_tables_are_registered() -> None:
    expected_tables = {
        "users",
        "auth_sessions",
        "source_credentials",
        "sources",
        "raw_items",
        "items",
        "topics",
        "topic_items",
        "digests",
        "digest_items",
        "user_preferences",
        "saved_searches",
        "user_feedback",
        "llm_providers",
        "prompt_versions",
        "llm_call_logs",
        "job_runs",
        "scheduler_configs",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_user_uniqueness_constraints_are_named() -> None:
    constraints = {constraint.name for constraint in Base.metadata.tables["users"].constraints}

    assert "ux_users_username" in constraints
    assert "ux_users_email" in constraints
