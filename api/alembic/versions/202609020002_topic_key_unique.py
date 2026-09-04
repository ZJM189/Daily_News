"""enforce unique topic aggregation keys

Revision ID: 202609020002
Revises: 202609020001
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202609020002"
down_revision: str | None = "202609020001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("idx_topics_normalized_key", table_name="topics")
    op.create_unique_constraint("ux_topics_normalized_key", "topics", ["normalized_key"])


def downgrade() -> None:
    op.drop_constraint("ux_topics_normalized_key", "topics", type_="unique")
    op.create_index("idx_topics_normalized_key", "topics", ["normalized_key"])
