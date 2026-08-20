"""initial

Revision ID: 001
Revises:
Create Date: 2026-08-21 01:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.Enum("once", "recurring", name="remindertype"), nullable=False),
        sa.Column("fire_at", sa.DateTime(), nullable=True),
        sa.Column("cron_day", sa.String(length=32), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("status", sa.Enum("active", "done", "cancelled", name="reminderstatus"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "reminder_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reminder_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.Enum("pending", "delivered", "failed", "unsubscribed", name="broadcaststatus"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reminder_id", "user_id", name="uq_reminder_recipient"),
    )
    op.create_index("ix_reminder_recipients_user_id", "reminder_recipients", ["user_id"], unique=False)
    op.create_table(
        "subscribers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("subscribed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("segment", sa.String(length=64), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("delivered", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("unsubscribed", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "broadcast_recipients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("broadcast_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "delivered", "failed", "unsubscribed", name="broadcaststatus"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("broadcast_id", "user_id", name="uq_broadcast_recipient"),
    )
    op.create_index("ix_broadcast_recipients_status", "broadcast_recipients", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_broadcast_recipients_status", table_name="broadcast_recipients")
    op.drop_table("broadcast_recipients")
    op.drop_table("broadcasts")
    op.drop_table("subscribers")
    op.drop_index("ix_reminder_recipients_user_id", table_name="reminder_recipients")
    op.drop_table("reminder_recipients")
    op.drop_table("reminders")
