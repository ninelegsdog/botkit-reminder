from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.reminder.models import Broadcast, BroadcastStatus, Reminder, ReminderRecipient, ReminderStatus
from src.reminder.service import ReminderService

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, session_factory: Callable[[], AsyncSession], send_callback: Callable[[int, str], Awaitable[None]]) -> None:
        self._session_factory = session_factory
        self._send_callback = send_callback
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.exception("Scheduler tick failed: %s", exc)
            await asyncio.sleep(settings.scheduler_interval_seconds)

    async def _tick(self) -> None:
        async with self._session_factory() as session:
            now = datetime.utcnow()
            stmt = select(Reminder).where(
                Reminder.status == ReminderStatus.active,
                Reminder.is_active == True,
                Reminder.fire_at != None,  # noqa: E711
                Reminder.fire_at <= now,
            )
            result = await session.execute(stmt)
            reminders = result.scalars().all()

            stmt2 = select(ReminderRecipient).where(ReminderRecipient.status == BroadcastStatus.pending)
            result2 = await session.execute(stmt2)
            recipients = result2.scalars().all()

        for reminder in reminders:
            try:
                await self._send_callback(reminder.creator_id, reminder.text)
            except Exception:
                logger.exception("Failed to send reminder %s", reminder.id)
            async with self._session_factory() as session:
                service = ReminderService(session, None)
                await service.mark_done(reminder.id)
                await session.commit()

        for rr in recipients:
            try:
                await self._send_callback(rr.user_id, "Напоминание")
                rr.status = BroadcastStatus.delivered
                rr.delivered_at = datetime.utcnow()
            except Exception:
                rr.status = BroadcastStatus.failed
