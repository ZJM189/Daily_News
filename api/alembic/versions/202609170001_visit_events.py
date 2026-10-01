"""Track anonymous public page visits.

Revision ID: 202609170001
Revises: 202609120001
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "202609170001"
down_revision = "202609120001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visit_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("visitor_id", sa.String(64), nullable=False),
        sa.Column("path", sa.String(255), nullable=False),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_visit_events_created_at", "visit_events", ["created_at"])
    op.create_index(
        "idx_visit_events_visitor_created_at",
        "visit_events",
        ["visitor_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_visit_events_visitor_created_at", table_name="visit_events")
    op.drop_index("idx_visit_events_created_at", table_name="visit_events")
    op.drop_table("visit_events")
