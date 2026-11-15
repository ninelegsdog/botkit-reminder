"""State-dependent view tests for reminder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.uow import UnitOfWork
from src.reminder.models import Reminder, ReminderStatus, ReminderType, Subscriber
from src.reminder.repositories import ReminderRepository, SubscriberRepository


@pytest.fixture
async def session_factory(tmp_path: Any) -> Any:
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.asyncio
async def test_reminders_by_creator_empty_vs_populated(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = ReminderRepository(uow)
        assert await repo.get_by_creator(1) == []

        session.add(
            Reminder(
                creator_id=1,
                type=ReminderType.once,
                text="hello",
                fire_at=datetime.now(UTC) + timedelta(hours=1),
                status=ReminderStatus.active,
                is_active=True,
            )
        )
        await session.commit()
        reminders = await repo.get_by_creator(1)
        assert len(reminders) == 1
        assert reminders[0].text == "hello"


@pytest.mark.asyncio
async def test_reminder_missing_vs_present(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = ReminderRepository(uow)
        assert await repo.get_by_id(99999) is None

        session.add(
            Reminder(
                creator_id=1,
                type=ReminderType.once,
                text="hello",
                fire_at=datetime.now(UTC) + timedelta(hours=1),
                status=ReminderStatus.active,
                is_active=True,
            )
        )
        await session.commit()
        # fetch the id
        from sqlalchemy import select
        res = await session.execute(select(Reminder))
        rid = res.scalars().first().id
        r = await repo.get_by_id(rid)
        assert r is not None
        assert r.text == "hello"


@pytest.mark.asyncio
async def test_subscriber_missing_vs_present(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = SubscriberRepository(uow)
        assert await repo.get_by_user_id(99999) is None

        session.add(Subscriber(user_id=42, username="u", name="U"))
        await session.commit()
        sub = await repo.get_by_user_id(42)
        assert sub is not None
        assert sub.user_id == 42


@pytest.mark.asyncio
async def test_get_pending_empty_vs_populated(session_factory: Any) -> None:
    from src.reminder.repositories import BroadcastRecipientRepository

    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = BroadcastRecipientRepository(uow)
        assert await repo.get_pending() == []
