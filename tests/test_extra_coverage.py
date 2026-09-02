from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.config import Settings
from src.core.database import Base
from src.core.metrics import Metrics
from src.core.uow import UnitOfWork
from src.reminder.models import Reminder, ReminderStatus, ReminderType, Subscriber
from src.reminder.repositories import ReminderRepository, SubscriberRepository
from src.reminder.scheduler import Scheduler
from src.reminder.service import ReminderService


@pytest.fixture
async def session_factory(tmp_path: Any) -> Any:
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.asyncio
async def test_reminder_repo_get_due_once(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = ReminderRepository(uow)
        session.add(Reminder(
            creator_id=1, type=ReminderType.once,
            fire_at=datetime.now(UTC) - timedelta(minutes=1),
            text="Test", is_active=True, status=ReminderStatus.active
        ))
        await session.flush()
        due = await repo.get_due_once(datetime.now(UTC))
        assert len(due) >= 1


@pytest.mark.asyncio
async def test_reminder_repo_get_recurring(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = ReminderRepository(uow)
        rec = await repo.get_recurring_by_weekday(datetime.now(UTC).weekday())
        assert isinstance(rec, list)


@pytest.mark.asyncio
async def test_subscriber_repo_get_active(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = SubscriberRepository(uow)
        session.add(Subscriber(user_id=1, username="user", name="Name", is_active=True))
        await session.flush()
        active = await repo.get_active("active")
        assert len(active) >= 1


@pytest.mark.asyncio
async def test_scheduler_error_handling(session_factory: Any) -> None:
    call_count = 0
    async def send_callback(user_id: int, text: str) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("test failure")

    scheduler = Scheduler(session_factory, send_callback)
    async with session_factory() as session:
        uow = UnitOfWork(session)
        _ = ReminderService(uow)
        fire_at = datetime.now(UTC) - timedelta(minutes=1)
        session.add(Reminder(
            creator_id=1, type=ReminderType.once, fire_at=fire_at,
            text="Test1", is_active=True, status=ReminderStatus.active
        ))
        session.add(Reminder(
            creator_id=1, type=ReminderType.once, fire_at=fire_at,
            text="Test2", is_active=True, status=ReminderStatus.active
        ))
        await session.flush()
        await session.commit()

    await scheduler._tick()
    assert call_count == 2


@pytest.mark.asyncio
async def test_metrics_attributes() -> None:
    m = Metrics()
    m.messages_processed = 1
    m.reminders_sent = 1
    m.errors = 1
    assert m.messages_processed == 1
    assert m.uptime_seconds() >= 0

@pytest.mark.asyncio
async def test_config_settings_validation() -> None:
    cfg = Settings(
        telegram_bot_token="123:ABC",
        admin_password="secret",
        admin_ids="1",
        telegram_webhook_secret="secret",
    )
    cfg.validate_on_startup()

    cfg2 = Settings(
        telegram_bot_token="",
        admin_password="secret",
        admin_ids="1",
        telegram_webhook_secret="secret",
    )
    with pytest.raises(RuntimeError):
        cfg2.validate_on_startup()
