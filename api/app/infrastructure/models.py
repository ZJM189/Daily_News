from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLEnum

from app.infrastructure.persistence import Base


def enum_values(enum_class: type[enum.Enum]) -> list[str]:
    return [item.value for item in enum_class]


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class SourceType(str, enum.Enum):
    RSS = "rss"
    HACKER_NEWS = "hacker_news"
    GITHUB = "github"
    ARXIV = "arxiv"
    PRODUCT_HUNT = "product_hunt"
    HUGGING_FACE = "hugging_face"


class SourceStatus(str, enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    MISSING_TOKEN = "missing_token"
    ERROR = "error"


class CredentialStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    MISSING = "missing"
    ERROR = "error"


class ItemStatus(str, enum.Enum):
    COLLECTED = "collected"
    NORMALIZED = "normalized"
    DEDUPED = "deduped"
    RANKED = "ranked"
    SUMMARIZED = "summarized"
    SELECTED = "selected"
    FAILED = "failed"


class CategoryCode(str, enum.Enum):
    MODEL_COMPANY = "model_company"
    OPEN_SOURCE = "open_source"
    RESEARCH_PAPER = "research_paper"
    PRODUCT_LAUNCH = "product_launch"
    COMMUNITY = "community"
    INDUSTRY_FUNDING = "industry_funding"
    OTHER = "other"


class DigestStatus(str, enum.Enum):
    GENERATING = "generating"
    PUBLISHED = "published"
    FAILED = "failed"


class JobType(str, enum.Enum):
    COLLECT = "collect"
    NORMALIZE = "normalize"
    DEDUPE = "dedupe"
    RANK = "rank"
    SUMMARIZE = "summarize"
    GENERATE_DIGEST = "generate_digest"
    PUBLISH_DIGEST = "publish_digest"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"


class JobTriggerType(str, enum.Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    RETRY = "retry"


class LLMProviderType(str, enum.Enum):
    OPENAI_COMPATIBLE = "openai_compatible"


class LLMCallStatus(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SCHEMA_ERROR = "schema_error"


class FeedbackAction(str, enum.Enum):
    MORE_LIKE = "more_like"
    LESS_LIKE = "less_like"
    BLOCK_SOURCE = "block_source"


user_role_enum = SQLEnum(UserRole, values_callable=enum_values, name="user_role")
user_status_enum = SQLEnum(UserStatus, values_callable=enum_values, name="user_status")
source_type_enum = SQLEnum(SourceType, values_callable=enum_values, name="source_type")
source_status_enum = SQLEnum(SourceStatus, values_callable=enum_values, name="source_status")
credential_status_enum = SQLEnum(
    CredentialStatus, values_callable=enum_values, name="credential_status"
)
item_status_enum = SQLEnum(ItemStatus, values_callable=enum_values, name="item_status")
category_code_enum = SQLEnum(CategoryCode, values_callable=enum_values, name="category_code")
digest_status_enum = SQLEnum(DigestStatus, values_callable=enum_values, name="digest_status")
job_type_enum = SQLEnum(JobType, values_callable=enum_values, name="job_type")
job_status_enum = SQLEnum(JobStatus, values_callable=enum_values, name="job_status")
job_trigger_type_enum = SQLEnum(
    JobTriggerType, values_callable=enum_values, name="job_trigger_type"
)
llm_provider_type_enum = SQLEnum(
    LLMProviderType, values_callable=enum_values, name="llm_provider_type"
)
llm_call_status_enum = SQLEnum(
    LLMCallStatus, values_callable=enum_values, name="llm_call_status"
)
feedback_action_enum = SQLEnum(
    FeedbackAction, values_callable=enum_values, name="feedback_action"
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="ux_users_username"),
        UniqueConstraint("email", name="ux_users_email"),
        Index("idx_users_role_status", "role", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(user_role_enum, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        user_status_enum, nullable=False, server_default=UserStatus.ACTIVE.value
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FavoriteFolder(Base, TimestampMixin):
    __tablename__ = "favorite_folders"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="ux_favorite_folders_user_name"),
        UniqueConstraint("user_id", "id", name="ux_favorite_folders_user_id"),
        CheckConstraint("length(trim(name)) > 0", name="ck_favorite_folders_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)


class Favorite(Base, TimestampMixin):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="ux_favorites_user_item"),
        ForeignKeyConstraint(
            ["user_id", "folder_id"], ["favorite_folders.user_id", "favorite_folders.id"],
            name="fk_favorites_owned_folder",
        ),
        Index("idx_favorites_user_created", "user_id", "created_at"),
        Index("idx_favorites_user_folder", "user_id", "folder_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id"), nullable=False)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class LibraryChatThread(Base, TimestampMixin):
    __tablename__ = "library_chat_threads"
    __table_args__ = (
        Index("idx_library_chat_threads_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)


class LibraryChatMessage(Base):
    __tablename__ = "library_chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_library_chat_messages_role"),
        Index("idx_library_chat_messages_thread_created", "thread_id", "created_at"),
        Index("idx_library_chat_messages_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("library_chat_threads.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="ux_auth_sessions_token_hash"),
        Index("idx_auth_sessions_user_id", "user_id"),
        Index("idx_auth_sessions_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SourceCredential(Base, TimestampMixin):
    __tablename__ = "source_credentials"
    __table_args__ = (
        Index("idx_source_credentials_type_status", "source_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(source_type_enum, nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    secret_masked: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[CredentialStatus] = mapped_column(
        credential_status_enum, nullable=False, server_default=CredentialStatus.ACTIVE.value
    )
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_test_status: Mapped[str | None] = mapped_column(String(32))
    last_test_error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Source(Base, TimestampMixin):
    __tablename__ = "sources"
    __table_args__ = (
        Index("idx_sources_type_status", "type", "status"),
        Index("idx_sources_status", "status"),
        CheckConstraint("weight >= 0 AND weight <= 100", name="ck_sources_weight_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[SourceType] = mapped_column(source_type_enum, nullable=False)
    status: Mapped[SourceStatus] = mapped_column(
        source_status_enum, nullable=False, server_default=SourceStatus.DISABLED.value
    )
    url: Mapped[str | None] = mapped_column(Text)
    query_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_credentials.id", ondelete="SET NULL")
    )
    credential_env_key: Mapped[str | None] = mapped_column(String(120))
    weight: Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")
    language: Mapped[str | None] = mapped_column(String(16))
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class LLMProvider(Base, TimestampMixin):
    __tablename__ = "llm_providers"
    __table_args__ = (
        UniqueConstraint("name", name="ux_llm_providers_name"),
        Index(
            "ux_llm_providers_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[LLMProviderType] = mapped_column(llm_provider_type_enum, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    api_key_masked: Mapped[str | None] = mapped_column(String(40))
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="60")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="2")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_test_status: Mapped[str | None] = mapped_column(String(32))
    last_test_error: Mapped[str | None] = mapped_column(Text)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="ux_prompt_versions_name_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (
        Index("idx_job_runs_type_status", "job_type", "status"),
        Index("idx_job_runs_started_at", "started_at"),
        Index("idx_job_runs_source_id", "source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    job_type: Mapped[JobType] = mapped_column(job_type_enum, nullable=False)
    trigger_type: Mapped[JobTriggerType] = mapped_column(job_trigger_type_enum, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        job_status_enum, nullable=False, server_default=JobStatus.PENDING.value
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL")
    )
    parent_job_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_runs.id", ondelete="SET NULL")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RawItem(Base):
    __tablename__ = "raw_items"
    __table_args__ = (
        UniqueConstraint("source_id", "raw_hash", name="ux_raw_items_source_raw_hash"),
        Index(
            "ux_raw_items_source_external_id",
            "source_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index("idx_raw_items_source_fetched_at", "source_id", "fetched_at"),
        Index("idx_raw_items_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    job_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_runs.id", ondelete="SET NULL")
    )
    source_type: Mapped[SourceType] = mapped_column(source_type_enum, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    raw_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[ItemStatus] = mapped_column(
        item_status_enum, nullable=False, server_default=ItemStatus.COLLECTED.value
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Item(Base, TimestampMixin):
    __tablename__ = "items"
    __table_args__ = (
        Index(
            "ux_items_source_external_id",
            "source_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index("idx_items_canonical_url", "canonical_url"),
        Index("idx_items_title_hash", "title_hash"),
        Index("idx_items_status_category", "status", "category"),
        Index("idx_items_source_published_at", "source_id", "published_at"),
        Index("idx_items_score_published_at", "score", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    raw_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("raw_items.id", ondelete="SET NULL")
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    summary_original: Mapped[str | None] = mapped_column(Text)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16))
    category: Mapped[CategoryCode] = mapped_column(
        category_code_enum, nullable=False, server_default=CategoryCode.OTHER.value
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY[]::text[]")
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[ItemStatus] = mapped_column(
        item_status_enum, nullable=False, server_default=ItemStatus.NORMALIZED.value
    )
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default="0")
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    summary_zh: Mapped[str | None] = mapped_column(Text)
    importance_zh: Mapped[str | None] = mapped_column(Text)
    summary_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    summarized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    llm_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_providers.id", ondelete="SET NULL")
    )
    llm_model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)


class Topic(Base, TimestampMixin):
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("normalized_key", name="ux_topics_normalized_key"),
        Index("idx_topics_score_last_seen", "score", "last_seen_at"),
        Index("idx_topics_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[CategoryCode] = mapped_column(
        category_code_enum, nullable=False, server_default=CategoryCode.OTHER.value
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY[]::text[]")
    )
    summary_zh: Mapped[str | None] = mapped_column(Text)
    importance_zh: Mapped[str | None] = mapped_column(Text)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default="0")
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    primary_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL")
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TopicItem(Base):
    __tablename__ = "topic_items"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="related")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Digest(Base):
    __tablename__ = "digests"
    __table_args__ = (
        UniqueConstraint("digest_date", "version", name="ux_digests_date_version"),
        Index("idx_digests_date_status", "digest_date", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    digest_date: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DigestStatus] = mapped_column(digest_status_enum, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    overview_zh: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    job_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_runs.id", ondelete="SET NULL")
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DigestItem(Base):
    __tablename__ = "digest_items"
    __table_args__ = (
        UniqueConstraint("digest_id", "rank", name="ux_digest_items_digest_rank"),
        CheckConstraint(
            "(item_id IS NOT NULL AND topic_id IS NULL) OR "
            "(item_id IS NULL AND topic_id IS NOT NULL)",
            name="ck_digest_items_one_target",
        ),
        Index("idx_digest_items_digest_id", "digest_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    digest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("digests.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL")
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL")
    )
    item_type: Mapped[str] = mapped_column(String(16), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score_snapshot: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    title_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    summary_snapshot_zh: Mapped[str | None] = mapped_column(Text)
    importance_snapshot_zh: Mapped[str | None] = mapped_column(Text)
    category_snapshot: Mapped[CategoryCode] = mapped_column(category_code_enum, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"
    __table_args__ = (
        Index("idx_user_preferences_keywords_gin", "follow_keywords", postgresql_using="gin"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    follow_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY[]::text[]")
    )
    exclude_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY[]::text[]")
    )
    follow_categories: Mapped[list[CategoryCode]] = mapped_column(
        ARRAY(category_code_enum),
        nullable=False,
        server_default=text("ARRAY[]::category_code[]"),
    )
    follow_source_types: Mapped[list[SourceType]] = mapped_column(
        ARRAY(source_type_enum),
        nullable=False,
        server_default=text("ARRAY[]::source_type[]"),
    )
    disabled_source_types: Mapped[list[SourceType]] = mapped_column(
        ARRAY(source_type_enum),
        nullable=False,
        server_default=text("ARRAY[]::source_type[]"),
    )
    blocked_source_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default=text("ARRAY[]::uuid[]")
    )
    blocked_domains: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY[]::text[]")
    )
    weights: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class SavedSearch(Base, TimestampMixin):
    __tablename__ = "saved_searches"
    __table_args__ = (
        Index("idx_saved_searches_user_enabled", "user_id", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    query: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    apply_as_filter: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    apply_as_boost: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    __table_args__ = (
        CheckConstraint(
            "(item_id IS NOT NULL AND topic_id IS NULL) OR "
            "(item_id IS NULL AND topic_id IS NOT NULL) OR "
            "(action = 'block_source' AND source_id IS NOT NULL)",
            name="ck_user_feedback_target",
        ),
        Index("idx_user_feedback_user_action", "user_id", "action"),
        Index("idx_user_feedback_item", "item_id"),
        Index("idx_user_feedback_topic", "topic_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE")
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE")
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE")
    )
    action: Mapped[FeedbackAction] = mapped_column(feedback_action_enum, nullable=False)
    reason_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY[]::text[]")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class LLMCallLog(Base):
    __tablename__ = "llm_call_logs"
    __table_args__ = (
        Index("idx_llm_call_logs_object", "object_type", "object_id"),
        Index("idx_llm_call_logs_provider_status", "provider_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("llm_providers.id", ondelete="SET NULL")
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="SET NULL")
    )
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[LLMCallStatus] = mapped_column(llm_call_status_enum, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SchedulerConfig(Base, TimestampMixin):
    __tablename__ = "scheduler_configs"
    __table_args__ = (
        Index("idx_scheduler_configs_job_enabled", "job_type", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    job_type: Mapped[JobType] = mapped_column(job_type_enum, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="Asia/Shanghai"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    params: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
