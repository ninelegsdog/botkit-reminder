from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class ReminderType(enum.StrEnum):
    once = "once"
    recurring = "recurring"


class ReminderStatus(enum.StrEnum):
    active = "active"
    done = "done"
    cancelled = "cancelled"


class BroadcastStatus(enum.StrEnum):
    pending = "pending"
    delivered = "delivered"
    failed = "failed"
    unsubscribed = "unsubscribed"


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[ReminderType] = mapped_column(SQLEnum(ReminderType), nullable=False)
    fire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cron_day: Mapped[str | None] = mapped_column(String(32), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        SQLEnum(ReminderStatus), default=ReminderStatus.active, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)  # noqa: DTZ005

    recipients: Mapped[list[ReminderRecipient]] = relationship(
        back_populates="reminder", cascade="all, delete-orphan"
    )


class ReminderRecipient(Base):
    __tablename__ = "reminder_recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    reminder_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reminders.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[BroadcastStatus] = mapped_column(
        SQLEnum(BroadcastStatus), default=BroadcastStatus.pending, nullable=False
    )

    reminder: Mapped[Reminder] = relationship(back_populates="recipients")

    __table_args__ = (
        UniqueConstraint("reminder_id", "user_id", name="uq_reminder_recipient"),
        Index("ix_reminder_recipients_user_id", "user_id"),
    )


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)  # noqa: DTZ005


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    segment: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unsubscribed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)  # noqa: DTZ005


class BroadcastRecipient(Base):
    __tablename__ = "broadcast_recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    broadcast_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BroadcastStatus] = mapped_column(
        SQLEnum(BroadcastStatus), default=BroadcastStatus.pending, nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("broadcast_id", "user_id", name="uq_broadcast_recipient"),
        Index("ix_broadcast_recipients_status", "status"),
    )
