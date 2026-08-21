from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.metrics import BROADCAST_SENT
from src.core.uow import UnitOfWork
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
from src.reminder.repositories import BroadcastRecipientRepository, ReminderRepository, SubscriberRepository

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, uow: UnitOfWork, bot: Bot | None = None) -> None:
        self._uow = uow
        self.bot = bot
        self._reminders = ReminderRepository(uow)
        self._subscribers = SubscriberRepository(uow)

    @property
    def session(self) -> AsyncSession:
        return self._uow.session

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
        return await self._reminders.get_due_once(now)

    async def get_recurring_due(self, weekday: int) -> Sequence[Reminder]:
        return await self._reminders.get_recurring_by_weekday(weekday)

    async def mark_done(self, reminder_id: int) -> None:
        await self._reminders.mark_done(reminder_id)

    async def cancel_reminder(self, reminder_id: int) -> None:
        reminder = await self._reminders.get_by_id(reminder_id)
        if reminder:
            reminder.status = ReminderStatus.cancelled
            reminder.is_active = False

    async def send_reminder(self, reminder: Reminder) -> None:
        if not self.bot:
            return
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

    async def get_user_reminders(self, creator_id: int) -> Sequence[Reminder]:
        return await self._reminders.get_by_creator(creator_id)

    async def get_subscriber(self, user_id: int) -> Subscriber | None:
        return await self._subscribers.get_by_user_id(user_id)


class BroadcastService:
    def __init__(self, uow: UnitOfWork, bot: Bot | None = None) -> None:
        self._uow = uow
        self.bot = bot
        self._recipients = BroadcastRecipientRepository(uow)
        self._subscribers = SubscriberRepository(uow)

    @property
    def session(self) -> AsyncSession:
        return self._uow.session

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

        subscribers = await self._subscribers.get_active(broadcast.segment)
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
                    await self._send_with_retry(self.bot, sub.user_id, broadcast.text)
                recipient.status = BroadcastStatus.delivered
                recipient.delivered_at = datetime.now(UTC)
                delivered += 1
                BROADCAST_SENT.labels(status="delivered").inc()
            except Exception:
                recipient.status = BroadcastStatus.failed
                failed += 1
                BROADCAST_SENT.labels(status="failed").inc()

        broadcast.total = total
        broadcast.delivered = delivered
        broadcast.failed = failed
        broadcast.unsubscribed = unsubscribed
        broadcast.sent_at = datetime.now(UTC)
        await self.session.flush()

    async def _send_with_retry(self, bot: Any, user_id: int, text: str, max_retries: int = 3) -> None:
        import asyncio

        for attempt in range(max_retries):
            try:
                await bot.send_message(user_id, text)
                return
            except TelegramRetryAfter as exc:
                logger.warning("Flood control for user %s, retry in %s sec", user_id, exc.retry_after)
                await asyncio.sleep(exc.retry_after)
            except TelegramNetworkError as exc:
                logger.warning("Network error for user %s, attempt %s: %s", user_id, attempt + 1, exc)
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"Failed to send broadcast to user {user_id} after {max_retries} retries")


class SubscriptionService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._subscribers = SubscriberRepository(uow)

    @property
    def session(self) -> AsyncSession:
        return self._uow.session

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
