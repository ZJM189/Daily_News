"""Add library chat threads and messages.

Revision ID: 202609080001
Revises: 202609060001
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "202609080001"
down_revision = "202609060001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "library_chat_threads",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "idx_library_chat_threads_user_updated",
        "library_chat_threads",
        ["user_id", "updated_at"],
    )

    op.create_table(
        "library_chat_messages",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "thread_id",
            UUID(as_uuid=True),
            sa.ForeignKey("library_chat_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_library_chat_messages_role"),
    )
    op.create_index(
        "idx_library_chat_messages_thread_created",
        "library_chat_messages",
        ["thread_id", "created_at"],
    )
    op.create_index(
        "idx_library_chat_messages_user_created",
        "library_chat_messages",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_library_chat_messages_user_created", table_name="library_chat_messages")
    op.drop_index("idx_library_chat_messages_thread_created", table_name="library_chat_messages")
    op.drop_table("library_chat_messages")
    op.drop_index("idx_library_chat_threads_user_updated", table_name="library_chat_threads")
    op.drop_table("library_chat_threads")
