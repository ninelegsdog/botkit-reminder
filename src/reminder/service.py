from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.reminder.models import (
    Broadcast,
    BroadcastRecipient,
    BroadcastStatus,
    Reminder,
    ReminderRecipient,
    ReminderStatus,
    ReminderType,
    Subscriber,
)


class ReminderService:
    def __init__(self, session: AsyncSession, bot: Bot) -> None:
        self.session = session
        self.bot = bot

    async def create_reminder(
        self,
        creator_id: int,
        type: ReminderType,
        text: str,
        fire_at: datetime | None = None,
        cron_day: str | None = None,
    ) -> Reminder:
        reminder = Reminder(
            creator_id=creator_id,
            type=type,
            fire_at=fire_at,
            cron_day=cron_day,
            text=text,
        )
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def add_recipient(self, reminder_id: int, user_id: int) -> ReminderRecipient:
        rr = ReminderRecipient(reminder_id=reminder_id, user_id=user_id)
        self.session.add(rr)
        await self.session.flush()
        return rr

    async def get_due_reminders(self, now: datetime) -> Sequence[Reminder]:
        stmt = select(Reminder).where(
            Reminder.type == ReminderType.once,
            Reminder.status == ReminderStatus.active,
            Reminder.is_active,
            Reminder.fire_at != None,  # noqa: E711
            Reminder.fire_at <= now,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recurring_due(self, weekday: int) -> Sequence[Reminder]:
        stmt = select(Reminder).where(
            Reminder.type == ReminderType.recurring,
            Reminder.status == ReminderStatus.active,
            Reminder.is_active,
            Reminder.cron_day == str(weekday),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_done(self, reminder_id: int) -> None:
        stmt = select(Reminder).where(Reminder.id == reminder_id)
        result = await self.session.execute(stmt)
        reminder = result.scalar_one_or_none()
        if reminder:
            reminder.status = ReminderStatus.done

    async def cancel_reminder(self, reminder_id: int) -> None:
        stmt = select(Reminder).where(Reminder.id == reminder_id)
        result = await self.session.execute(stmt)
        reminder = result.scalar_one_or_none()
        if reminder:
            reminder.status = ReminderStatus.cancelled
            reminder.is_active = False

    async def send_reminder(self, reminder: Reminder) -> None:
        recipients = await self._get_recipients(reminder.id)
        for rr in recipients:
            try:
                await self.bot.send_message(rr.user_id, f"⏰ {reminder.text}")
                rr.status = BroadcastStatus.delivered
                rr.delivered_at = datetime.now(UTC)
            except Exception:
                rr.status = BroadcastStatus.failed
        await self.session.flush()

    async def _get_recipients(self, reminder_id: int) -> Sequence[ReminderRecipient]:
        stmt = select(ReminderRecipient).where(
            ReminderRecipient.reminder_id == reminder_id,
            ReminderRecipient.status == BroadcastStatus.pending,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class BroadcastService:
    def __init__(self, session: AsyncSession, bot: Bot) -> None:
        self.session = session
        self.bot = bot

    async def create_broadcast(self, text: str, segment: str) -> Broadcast:
        broadcast = Broadcast(text=text, segment=segment)
        self.session.add(broadcast)
        await self.session.flush()
        return broadcast

    async def send_broadcast(self, broadcast_id: int) -> None:
        stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
        result = await self.session.execute(stmt)
        broadcast = result.scalar_one_or_none()
        if not broadcast:
            return

        subscribers = await self._get_subscribers(broadcast.segment)
        total = 0
        delivered = 0
        failed = 0
        unsubscribed = 0

        for sub in subscribers:
            total += 1
            recipient = BroadcastRecipient(broadcast_id=broadcast_id, user_id=sub.user_id)
            self.session.add(recipient)
            await self.session.flush()
            if not sub.is_active:
                recipient.status = BroadcastStatus.unsubscribed
                unsubscribed += 1
                continue
            try:
                if self.bot:
                    await self.bot.send_message(sub.user_id, broadcast.text)
                recipient.status = BroadcastStatus.delivered
                recipient.delivered_at = datetime.now(UTC)
                delivered += 1
            except Exception:
                recipient.status = BroadcastStatus.failed
                failed += 1

        broadcast.total = total
        broadcast.delivered = delivered
        broadcast.failed = failed
        broadcast.unsubscribed = unsubscribed
        broadcast.sent_at = datetime.now(UTC)
        await self.session.flush()

    async def _get_subscribers(self, segment: str) -> Sequence[Subscriber]:
        stmt = select(Subscriber).where(Subscriber.is_active)
        if segment == "active":
            pass
        result = await self.session.execute(stmt)
        return result.scalars().all()


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def subscribe(self, user_id: int, username: str | None, name: str | None) -> Subscriber:
        stmt = select(Subscriber).where(Subscriber.user_id == user_id)
        result = await self.session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub:
            sub.is_active = True
            sub.username = username
            sub.name = name
        else:
            sub = Subscriber(user_id=user_id, username=username, name=name)
            self.session.add(sub)
        await self.session.flush()
        return sub

    async def unsubscribe(self, user_id: int) -> None:
        stmt = select(Subscriber).where(Subscriber.user_id == user_id)
        result = await self.session.execute(stmt)
        sub = result.scalar_one_or_none()
        if sub:
            sub.is_active = False

    async def get_subscriber(self, user_id: int) -> Subscriber | None:
        stmt = select(Subscriber).where(Subscriber.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
