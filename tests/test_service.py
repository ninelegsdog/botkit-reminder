from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base
from src.reminder.models import Reminder, ReminderStatus, ReminderType
from src.reminder.service import ReminderService, SubscriptionService


@pytest.fixture
async def session_factory(tmp_path: Any) -> Any:
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.asyncio
async def test_get_due_reminders(session_factory: Any) -> None:
    async with session_factory() as session:
        service = ReminderService(session, None)
        fire_at = datetime.now(UTC) - timedelta(minutes=1)
        await service.create_reminder(1, ReminderType.once, "Past", fire_at=fire_at)
        future = datetime.now(UTC) + timedelta(hours=1)
        await service.create_reminder(1, ReminderType.once, "Future", fire_at=future)
        await session.commit()
        due = await service.get_due_reminders(datetime.now(UTC))
        assert len(due) == 1
        assert due[0].text == "Past"


@pytest.mark.asyncio
async def test_mark_done(session_factory: Any) -> None:
    async with session_factory() as session:
        service = ReminderService(session, None)
        fire_at = datetime.now(UTC) - timedelta(minutes=1)
        reminder = await service.create_reminder(1, ReminderType.once, "Test", fire_at=fire_at)
        await session.commit()
        await service.mark_done(reminder.id)
        await session.commit()
        updated = await session.get(Reminder, reminder.id)
        assert updated.status == ReminderStatus.done


@pytest.mark.asyncio
async def test_cancel_reminder(session_factory: Any) -> None:
    async with session_factory() as session:
        service = ReminderService(session, None)
        fire_at = datetime.now(UTC) - timedelta(minutes=1)
        reminder = await service.create_reminder(1, ReminderType.once, "Test", fire_at=fire_at)
        await session.commit()
        await service.cancel_reminder(reminder.id)
        await session.commit()
        updated = await session.get(Reminder, reminder.id)
        assert updated.status == ReminderStatus.cancelled
        assert updated.is_active is False


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe(session_factory: Any) -> None:
    async with session_factory() as session:
        service = SubscriptionService(session)
        sub = await service.subscribe(1, "user", "Name")
        assert sub.is_active is True
        await service.unsubscribe(1)
        assert sub.is_active is False
