from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.core.metrics import REMINDERS_SENT, SCHEDULER_ERRORS, SCHEDULER_TICKS
from src.core.uow import UnitOfWork
from src.reminder.models import (
    BroadcastStatus,
    Reminder,
    ReminderStatus,
    ReminderType,
)
from src.reminder.repositories import BroadcastRecipientRepository
from src.reminder.service import ReminderService

logger = logging.getLogger(__name__)

# Guards recurring reminders against per-tick spam: at most one send per
# (reminder, calendar-minute). Process-local; resets on restart (rare dup).
_RECURRING_SENT_MINUTE: dict[int, str] = {}


class Scheduler:
    def __init__(
        self,
        session_factory: Callable[[], Any],
        send_callback: Callable[[int, str], Awaitable[None]],
    ) -> None:
        self._session_factory = session_factory
        self._send_callback = send_callback
        self._scheduler = AsyncIOScheduler(
            jobstores={
                "default": SQLAlchemyJobStore(
                    url=settings.database_url.replace("sqlite+aiosqlite://", "sqlite://")
                ),
            },
            timezone=settings.tz,
        )

    def start(self) -> None:
        self._scheduler.add_job(
            scheduler_tick,
            "interval",
            seconds=settings.scheduler_interval_seconds,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=settings.scheduler_interval_seconds * 2,
            id="scheduler_tick",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("Scheduler started with persistent job store")

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")

    async def _tick(self) -> None:
        await scheduler_tick(self._session_factory, self._send_callback)


async def scheduler_tick(
    session_factory: Any = None,
    send_callback: Any = None,
) -> None:
    SCHEDULER_TICKS.labels(status="started").inc()
    try:
        from src.core.bot_factory import state
        from src.core.database import async_session

        if send_callback is None:
            send_callback = state.bot.send_message
        if session_factory is None:
            session_factory = async_session

        async with session_factory() as session:
            now = datetime.now(UTC)
            weekday = now.weekday()

            uow = UnitOfWork(session)
            reminder_repo = ReminderRepository(uow)
            recipient_repo = BroadcastRecipientRepository(uow)

            due_once = await reminder_repo.get_due_once_with_recipients(now)
            due_recurring = await reminder_repo.get_recurring_by_weekday_with_recipients(weekday)
            pending_recipients = await recipient_repo.get_pending()

            for reminder in due_once:
                recipients = [r.user_id for r in reminder.recipients]
                if reminder.creator_id not in recipients:
                    recipients.append(reminder.creator_id)
                for user_id in recipients:
                    try:
                        await send_callback(user_id, reminder.text)
                        REMINDERS_SENT.labels(type=reminder.type.value).inc()
                    except Exception:
                        SCHEDULER_ERRORS.labels(error_type="send").inc()
                        logger.exception("Failed to send reminder %s to user %s", reminder.id, user_id)
                service = ReminderService(uow)
                await service.mark_done(reminder.id)

            for reminder in due_recurring:
                if not reminder.fire_at:
                    continue
                if (now.hour, now.minute) != (reminder.fire_at.hour, reminder.fire_at.minute):
                    continue
                minute_key = f"{now.date().isoformat()}-{now.hour:02d}-{now.minute:02d}"
                if _RECURRING_SENT_MINUTE.get(reminder.id) == minute_key:
                    continue
                _RECURRING_SENT_MINUTE[reminder.id] = minute_key
                recipients = [r.user_id for r in reminder.recipients]
                if reminder.creator_id not in recipients:
                    recipients.append(reminder.creator_id)
                for user_id in recipients:
                    try:
                        await send_callback(user_id, reminder.text)
                        REMINDERS_SENT.labels(type=reminder.type.value).inc()
                    except Exception:
                        SCHEDULER_ERRORS.labels(error_type="send").inc()
                        logger.exception("Failed to send recurring reminder %s to user %s", reminder.id, user_id)

            for rr in pending_recipients:
                try:
                    await send_callback(rr.user_id, "Напоминание")
                    rr.status = BroadcastStatus.delivered
                    rr.delivered_at = datetime.now(UTC)
                except Exception:
                    rr.status = BroadcastStatus.failed
            SCHEDULER_TICKS.labels(status="success").inc()
    except Exception as exc:
        SCHEDULER_ERRORS.labels(error_type="tick").inc()
        SCHEDULER_TICKS.labels(status="failed").inc()
        logger.exception("Scheduler tick failed: %s", exc)


class ReminderRepository:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    @property
    def _session(self) -> Any:
        return self._uow.session

    async def get_due_once_with_recipients(self, now: datetime) -> Any:
        stmt = (
            select(Reminder)
            .where(
                Reminder.type == ReminderType.once,
                Reminder.status == ReminderStatus.active,
                Reminder.is_active,
                Reminder.fire_at is not None,
                Reminder.fire_at <= now,
            )
            .options(selectinload(Reminder.recipients))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_recurring_by_weekday_with_recipients(self, weekday: int) -> Any:
        stmt = (
            select(Reminder)
            .where(
                Reminder.type == ReminderType.recurring,
                Reminder.status == ReminderStatus.active,
                Reminder.is_active,
                Reminder.fire_at is not None,
                Reminder.cron_day == str(weekday),
            )
            .options(selectinload(Reminder.recipients))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
