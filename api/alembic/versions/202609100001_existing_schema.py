"""Reconcile the database revision already used by deployed environments.

Revision ID: 202609100001
Revises: 202609080001

The deployed database already contains the schema changes represented by this
revision, but the original migration file is not present in this checkout.
Keeping a no-op revision here restores the migration chain so later migrations
can be applied without changing existing data.
"""

revision = "202609100001"
down_revision = "202609080001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
