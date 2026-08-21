from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.reminder.models import Reminder, ReminderRecipient, ReminderStatus, ReminderType, Subscriber


class ReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_due_once(self, now: datetime) -> Sequence[Reminder]:
        stmt = select(Reminder).where(
            Reminder.type == ReminderType.once,
            Reminder.status == ReminderStatus.active,
            Reminder.is_active,
            Reminder.fire_at != None,  # noqa: E711
            Reminder.fire_at <= now,
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_recurring_by_weekday(self, weekday: int) -> Sequence[Reminder]:
        stmt = select(Reminder).where(
            Reminder.type == ReminderType.recurring,
            Reminder.status == ReminderStatus.active,
            Reminder.is_active,
            Reminder.cron_day == str(weekday),
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def mark_done(self, reminder_id: int) -> None:
        stmt = update(Reminder).where(Reminder.id == reminder_id).values(status=ReminderStatus.done)
        await self._session.execute(stmt)

    async def get_by_id(self, reminder_id: int) -> Reminder | None:
        stmt = select(Reminder).where(Reminder.id == reminder_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_creator(self, creator_id: int) -> Sequence[Reminder]:
        stmt = select(Reminder).where(Reminder.creator_id == creator_id).order_by(Reminder.id.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()


class BroadcastRecipientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_pending(self) -> Sequence[ReminderRecipient]:
        from src.reminder.models import BroadcastStatus
        stmt = select(ReminderRecipient).where(ReminderRecipient.status == BroadcastStatus.pending)
        result = await self._session.execute(stmt)
        return result.scalars().all()


class SubscriberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, segment: str) -> Sequence[Subscriber]:
        stmt = select(Subscriber).where(Subscriber.is_active)
        if segment == "active":
            pass
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_user_id(self, user_id: int) -> Subscriber | None:
        stmt = select(Subscriber).where(Subscriber.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
