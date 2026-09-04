"""initial schema

Revision ID: 202609020001
Revises:
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202609020001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role = postgresql.ENUM("user", "admin", name="user_role", create_type=False)
user_status = postgresql.ENUM("active", "disabled", name="user_status", create_type=False)
source_type = postgresql.ENUM(
    "rss",
    "hacker_news",
    "github",
    "arxiv",
    "product_hunt",
    "hugging_face",
    name="source_type",
    create_type=False,
)
source_status = postgresql.ENUM(
    "enabled", "disabled", "missing_token", "error", name="source_status", create_type=False
)
credential_status = postgresql.ENUM(
    "active", "disabled", "missing", "error", name="credential_status", create_type=False
)
item_status = postgresql.ENUM(
    "collected",
    "normalized",
    "deduped",
    "ranked",
    "summarized",
    "selected",
    "failed",
    name="item_status",
    create_type=False,
)
category_code = postgresql.ENUM(
    "model_company",
    "open_source",
    "research_paper",
    "product_launch",
    "community",
    "industry_funding",
    "other",
    name="category_code",
    create_type=False,
)
digest_status = postgresql.ENUM(
    "generating", "published", "failed", name="digest_status", create_type=False
)
job_type = postgresql.ENUM(
    "collect",
    "normalize",
    "dedupe",
    "rank",
    "summarize",
    "generate_digest",
    "publish_digest",
    name="job_type",
    create_type=False,
)
job_status = postgresql.ENUM(
    "pending",
    "running",
    "success",
    "failed",
    "partial_success",
    "cancelled",
    name="job_status",
    create_type=False,
)
job_trigger_type = postgresql.ENUM(
    "scheduled", "manual", "retry", name="job_trigger_type", create_type=False
)
llm_provider_type = postgresql.ENUM(
    "openai_compatible", name="llm_provider_type", create_type=False
)
llm_call_status = postgresql.ENUM(
    "success", "failed", "timeout", "schema_error", name="llm_call_status", create_type=False
)
feedback_action = postgresql.ENUM(
    "more_like", "less_like", "block_source", name="feedback_action", create_type=False
)


def create_enums() -> None:
    bind = op.get_bind()
    for enum_type in (
        user_role,
        user_status,
        source_type,
        source_status,
        credential_status,
        item_status,
        category_code,
        digest_status,
        job_type,
        job_status,
        job_trigger_type,
        llm_provider_type,
        llm_call_status,
        feedback_action,
    ):
        enum_type.create(bind, checkfirst=True)


def drop_enums() -> None:
    bind = op.get_bind()
    for enum_type in (
        feedback_action,
        llm_call_status,
        llm_provider_type,
        job_trigger_type,
        job_status,
        job_type,
        digest_status,
        category_code,
        item_status,
        credential_status,
        source_status,
        source_type,
        user_status,
        user_role,
    ):
        enum_type.drop(bind, checkfirst=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    create_enums()

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "status",
            user_status,
            nullable=False,
            server_default=sa.text("'active'::user_status"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("email", name="ux_users_email"),
        sa.UniqueConstraint("username", name="ux_users_username"),
    )
    op.create_index("idx_users_role_status", "users", ["role", "status"])

    op.create_table(
        "auth_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("ip_hash", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="ux_auth_sessions_token_hash"),
    )
    op.create_index("idx_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("idx_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table(
        "source_credentials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("secret_masked", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            credential_status,
            nullable=False,
            server_default=sa.text("'active'::credential_status"),
        ),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "idx_source_credentials_type_status", "source_credentials", ["source_type", "status"]
    )

    op.create_table(
        "sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", source_type, nullable=False),
        sa.Column(
            "status",
            source_status,
            nullable=False,
            server_default=sa.text("'disabled'::source_status"),
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("query_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credential_env_key", sa.String(length=120), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("weight >= 0 AND weight <= 100", name="ck_sources_weight_range"),
        sa.ForeignKeyConstraint(["credential_id"], ["source_credentials.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_sources_type_status", "sources", ["type", "status"])
    op.create_index("idx_sources_status", "sources", ["status"])

    op.create_table(
        "llm_providers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", llm_provider_type, nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("api_key_masked", sa.String(length=40), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", name="ux_llm_providers_name"),
    )
    op.create_index(
        "ux_llm_providers_default",
        "llm_providers",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.create_table(
        "prompt_versions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("output_schema", postgresql.JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", "version", name="ux_prompt_versions_name_version"),
    )

    op.create_table(
        "job_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("trigger_type", job_trigger_type, nullable=False),
        sa.Column(
            "status",
            job_status,
            nullable=False,
            server_default=sa.text("'pending'::job_status"),
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_job_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_detail", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_job_run_id"], ["job_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_job_runs_type_status", "job_runs", ["job_type", "status"])
    op.create_index("idx_job_runs_started_at", "job_runs", ["started_at"])
    op.create_index("idx_job_runs_source_id", "job_runs", ["source_id"])

    op.create_table(
        "raw_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("raw_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            item_status,
            nullable=False,
            server_default=sa.text("'collected'::item_status"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_run_id"], ["job_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.UniqueConstraint("source_id", "raw_hash", name="ux_raw_items_source_raw_hash"),
    )
    op.create_index(
        "ux_raw_items_source_external_id",
        "raw_items",
        ["source_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index("idx_raw_items_source_fetched_at", "raw_items", ["source_id", "fetched_at"])
    op.create_index("idx_raw_items_status", "raw_items", ["status"])

    op.create_table(
        "items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("title_hash", sa.String(length=64), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("summary_original", sa.Text(), nullable=True),
        sa.Column("content_snippet", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column(
            "category",
            category_code,
            nullable=False,
            server_default=sa.text("'other'::category_code"),
        ),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("ARRAY[]::text[]")),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "status",
            item_status,
            nullable=False,
            server_default=sa.text("'normalized'::item_status"),
        ),
        sa.Column("score", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("score_breakdown", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary_zh", sa.Text(), nullable=True),
        sa.Column("importance_zh", sa.Text(), nullable=True),
        sa.Column("summary_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("summarized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("llm_provider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["llm_provider_id"], ["llm_providers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["raw_item_id"], ["raw_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
    )
    op.create_index(
        "ux_items_source_external_id",
        "items",
        ["source_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_index("idx_items_canonical_url", "items", ["canonical_url"])
    op.create_index("idx_items_title_hash", "items", ["title_hash"])
    op.create_index("idx_items_status_category", "items", ["status", "category"])
    op.create_index("idx_items_source_published_at", "items", ["source_id", "published_at"])
    op.create_index("idx_items_score_published_at", "items", ["score", "published_at"])
    op.create_index("idx_items_tags_gin", "items", ["tags"], postgresql_using="gin")
    op.execute(
        """
        CREATE INDEX idx_items_search_tsv
        ON items
        USING gin (
            to_tsvector(
                'simple'::regconfig,
                coalesce(title, '') || ' ' ||
                coalesce(summary_zh, '') || ' ' ||
                coalesce(summary_original, '')
            )
        )
        """
    )

    op.create_table(
        "topics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_key", sa.String(length=128), nullable=False),
        sa.Column(
            "category",
            category_code,
            nullable=False,
            server_default=sa.text("'other'::category_code"),
        ),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("ARRAY[]::text[]")),
        sa.Column("summary_zh", sa.Text(), nullable=True),
        sa.Column("importance_zh", sa.Text(), nullable=True),
        sa.Column("score", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["primary_item_id"], ["items.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_topics_score_last_seen", "topics", ["score", "last_seen_at"])
    op.create_index("idx_topics_category", "topics", ["category"])
    op.create_index("idx_topics_normalized_key", "topics", ["normalized_key"])

    op.create_table(
        "topic_items",
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False, server_default="related"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("topic_id", "item_id"),
    )

    op.create_table(
        "digests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", digest_status, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("overview_zh", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("job_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_run_id"], ["job_runs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("digest_date", "version", name="ux_digests_date_version"),
    )
    op.create_index("idx_digests_date_status", "digests", ["digest_date", "status"])

    op.create_table(
        "digest_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("digest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_type", sa.String(length=16), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score_snapshot", sa.Numeric(6, 2), nullable=False),
        sa.Column("title_snapshot", sa.Text(), nullable=False),
        sa.Column("summary_snapshot_zh", sa.Text(), nullable=True),
        sa.Column("importance_snapshot_zh", sa.Text(), nullable=True),
        sa.Column("category_snapshot", category_code, nullable=False),
        sa.Column("source_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(item_id IS NOT NULL AND topic_id IS NULL) OR "
            "(item_id IS NULL AND topic_id IS NOT NULL)",
            name="ck_digest_items_one_target",
        ),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("digest_id", "rank", name="ux_digest_items_digest_rank"),
    )
    op.create_index("idx_digest_items_digest_id", "digest_items", ["digest_id"])

    op.create_table(
        "user_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "follow_keywords",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column(
            "exclude_keywords",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column(
            "follow_categories",
            postgresql.ARRAY(category_code),
            nullable=False,
            server_default=sa.text("ARRAY[]::category_code[]"),
        ),
        sa.Column(
            "follow_source_types",
            postgresql.ARRAY(source_type),
            nullable=False,
            server_default=sa.text("ARRAY[]::source_type[]"),
        ),
        sa.Column(
            "disabled_source_types",
            postgresql.ARRAY(source_type),
            nullable=False,
            server_default=sa.text("ARRAY[]::source_type[]"),
        ),
        sa.Column(
            "blocked_source_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("ARRAY[]::uuid[]"),
        ),
        sa.Column(
            "blocked_domains",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column("weights", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "idx_user_preferences_keywords_gin",
        "user_preferences",
        ["follow_keywords"],
        postgresql_using="gin",
    )

    op.create_table(
        "saved_searches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("query", postgresql.JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("apply_as_filter", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("apply_as_boost", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_saved_searches_user_enabled", "saved_searches", ["user_id", "enabled"])

    op.create_table(
        "user_feedback",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", feedback_action, nullable=False),
        sa.Column(
            "reason_tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY[]::text[]"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(item_id IS NOT NULL AND topic_id IS NULL) OR "
            "(item_id IS NULL AND topic_id IS NOT NULL) OR "
            "(action = 'block_source' AND source_id IS NOT NULL)",
            name="ck_user_feedback_target",
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_user_feedback_user_action", "user_feedback", ["user_id", "action"])
    op.create_index("idx_user_feedback_item", "user_feedback", ["item_id"])
    op.create_index("idx_user_feedback_topic", "user_feedback", ["topic_id"])

    op.create_table(
        "llm_call_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("object_type", sa.String(length=32), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", llm_call_status, nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provider_id"], ["llm_providers.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_llm_call_logs_object", "llm_call_logs", ["object_type", "object_id"])
    op.create_index("idx_llm_call_logs_provider_status", "llm_call_logs", ["provider_id", "status"])

    op.create_table(
        "scheduler_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("cron_expression", sa.String(length=120), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Shanghai"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_scheduler_configs_job_enabled", "scheduler_configs", ["job_type", "enabled"])

    op.execute(
        """
        INSERT INTO scheduler_configs (job_type, name, cron_expression, timezone, enabled, params)
        VALUES ('generate_digest', 'Daily AI Digest', '0 8 * * *', 'Asia/Shanghai', true, '{}'::jsonb)
        """
    )


def downgrade() -> None:
    op.drop_table("scheduler_configs")
    op.drop_table("llm_call_logs")
    op.drop_table("user_feedback")
    op.drop_table("saved_searches")
    op.drop_table("user_preferences")
    op.drop_table("digest_items")
    op.drop_table("digests")
    op.drop_table("topic_items")
    op.drop_index("idx_items_search_tsv", table_name="items")
    op.drop_table("topics")
    op.drop_table("items")
    op.drop_table("raw_items")
    op.drop_table("job_runs")
    op.drop_table("prompt_versions")
    op.drop_table("llm_providers")
    op.drop_table("sources")
    op.drop_table("source_credentials")
    op.drop_table("auth_sessions")
    op.drop_table("users")
    drop_enums()
