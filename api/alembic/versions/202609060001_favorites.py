"""Add private favorites and single-level folders.

Revision ID: 202609060001
Revises: 202609020002
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "202609060001"
down_revision = "202609020002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favorite_folders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "name", name="ux_favorite_folders_user_name"),
        sa.UniqueConstraint("user_id", "id", name="ux_favorite_folders_user_id"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_favorite_folders_name"),
    )
    op.create_table(
        "favorites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("folder_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "item_id", name="ux_favorites_user_item"),
        sa.ForeignKeyConstraint(
            ["user_id", "folder_id"],
            ["favorite_folders.user_id", "favorite_folders.id"],
            name="fk_favorites_owned_folder",
        ),
    )
    op.create_index("idx_favorites_user_created", "favorites", ["user_id", "created_at"])
    op.create_index("idx_favorites_user_folder", "favorites", ["user_id", "folder_id"])


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("favorite_folders")
