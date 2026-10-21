"""subscription_events audit log (F6)

Revision ID: 002
Revises: 001
Create Date: 2026-10-21 12:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscription_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subscription_events_user_id", "subscription_events", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_subscription_events_user_id", table_name="subscription_events")
    op.drop_table("subscription_events")
