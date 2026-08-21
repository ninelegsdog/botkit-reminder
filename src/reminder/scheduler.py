from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.metrics import REMINDERS_SENT, SCHEDULER_ERRORS, SCHEDULER_TICKS
from src.core.uow import UnitOfWork
from src.reminder.models import BroadcastStatus, Reminder, ReminderRecipient, ReminderStatus, ReminderType
from src.reminder.service import ReminderService

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        send_callback: Callable[[int, str], Awaitable[None]],
    ) -> None:
        self._session_factory = session_factory
        self._send_callback = send_callback
        self._scheduler = AsyncIOScheduler(
            jobstores={
                "default": SQLAlchemyJobStore(url=settings.database_url),
            },
            timezone=settings.tz,
        )

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick,
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
        SCHEDULER_TICKS.labels(status="started").inc()
        try:
            async with self._session_factory() as session:
                now = datetime.now(UTC)

                once_stmt = select(Reminder).where(
                    Reminder.type == ReminderType.once,
                    Reminder.status == ReminderStatus.active,
                    Reminder.is_active,
                    Reminder.fire_at != None,  # noqa: E711
                    Reminder.fire_at <= now,
                )
                once_result = await session.execute(once_stmt)
                due_once = once_result.scalars().all()

                recurring_stmt = select(Reminder).where(
                    Reminder.type == ReminderType.recurring,
                    Reminder.status == ReminderStatus.active,
                    Reminder.is_active,
                )
                recurring_result = await session.execute(recurring_stmt)
                due_recurring = recurring_result.scalars().all()

                pending_recipients_stmt = select(ReminderRecipient).where(
                    ReminderRecipient.status == BroadcastStatus.pending
                )
                pending_result = await session.execute(pending_recipients_stmt)
                pending_recipients = pending_result.scalars().all()

                uow = UnitOfWork(session)
                for reminder in due_once:
                    try:
                        await self._send_callback(reminder.creator_id, reminder.text)
                        REMINDERS_SENT.labels(type=reminder.type.value).inc()
                    except Exception:
                        SCHEDULER_ERRORS.labels(error_type="send").inc()
                        logger.exception("Failed to send reminder %s", reminder.id)
                    service = ReminderService(uow)
                    await service.mark_done(reminder.id)

                for reminder in due_recurring:
                    cron_day = reminder.cron_day
                    if cron_day is None:
                        continue
                    try:
                        if datetime.now(UTC).weekday() == int(cron_day):
                            await self._send_callback(reminder.creator_id, reminder.text)
                            REMINDERS_SENT.labels(type=reminder.type.value).inc()
                    except Exception:
                        SCHEDULER_ERRORS.labels(error_type="send").inc()
                        logger.exception("Failed to send recurring reminder %s", reminder.id)

                for rr in pending_recipients:
                    try:
                        await self._send_callback(rr.user_id, "Напоминание")
                        rr.status = BroadcastStatus.delivered
                        rr.delivered_at = datetime.now(UTC)
                    except Exception:
                        rr.status = BroadcastStatus.failed
            SCHEDULER_TICKS.labels(status="success").inc()
        except Exception as exc:
            SCHEDULER_ERRORS.labels(error_type="tick").inc()
            SCHEDULER_TICKS.labels(status="failed").inc()
            logger.exception("Scheduler tick failed: %s", exc)
