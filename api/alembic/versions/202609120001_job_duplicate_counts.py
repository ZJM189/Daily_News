"""Track duplicate items separately from successful job items.

Revision ID: 202609120001
Revises: 202609100001
"""

import sqlalchemy as sa

from alembic import op

revision = "202609120001"
down_revision = "202609100001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_runs",
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
    )
    # Preserve the useful duplicate signal for completed collect/normalize runs
    # created before this column existed. Other job types already count every
    # selected item as either successful or failed.
    op.execute(
        sa.text(
            """
            UPDATE job_runs
            SET duplicate_count = GREATEST(total_count - success_count - failure_count, 0)
            WHERE job_type IN ('collect', 'normalize')
              AND status IN ('success', 'partial_success', 'failed')
            """
        )
    )


def downgrade() -> None:
    op.drop_column("job_runs", "duplicate_count")
