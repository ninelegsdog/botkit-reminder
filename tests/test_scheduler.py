from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.reminder.models import Base, ReminderType
from src.reminder.scheduler import Scheduler


@pytest.fixture
async def session_factory(tmp_path):
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.asyncio
async def test_scheduler_sends_due_reminders(session_factory):
    sent = []

    async def send_callback(user_id: int, text: str) -> None:
        sent.append((user_id, text))

    scheduler = Scheduler(session_factory, send_callback)
    async with session_factory() as session:
        from src.reminder.service import ReminderService
        service = ReminderService(session, None)
        fire_at = datetime.now(UTC) - timedelta(minutes=1)
        await service.create_reminder(1, ReminderType.once, "Due", fire_at=fire_at)
        await session.commit()

    scheduler._running = True
    await scheduler._tick()
    assert len(sent) == 1
    assert sent[0] == (1, "Due")
