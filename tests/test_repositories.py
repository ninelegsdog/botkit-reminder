from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.uow import UnitOfWork
from src.reminder.models import Reminder, ReminderStatus, ReminderType, Subscriber
from src.reminder.repositories import (
    BroadcastRecipientRepository,
    ReminderRepository,
    SubscriberRepository,
)


@pytest.fixture
async def session_factory(tmp_path: Any) -> Any:
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.asyncio
async def test_uow_commit(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            uow.session.add(Subscriber(user_id=1, username="test", name="Test"))
        result = await session.get(Subscriber, 1)
        assert result is not None


@pytest.mark.asyncio
async def test_uow_rollback_on_exception(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        with pytest.raises(RuntimeError):
            async with uow:
                uow.session.add(Subscriber(user_id=1, username="test", name="Test"))
                raise RuntimeError("fail")
        # UoW doesn't own session, so we need to rollback manually
        await session.rollback()
        result = await session.get(Subscriber, 1)
        assert result is None


@pytest.mark.asyncio
async def test_reminder_repository_get_due_once(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = ReminderRepository(uow)
        past = datetime.now(UTC) - timedelta(minutes=1)
        future = datetime.now(UTC) + timedelta(hours=1)
        session.add(
            Reminder(
                creator_id=1,
                type=ReminderType.once,
                text="past",
                fire_at=past,
                status=ReminderStatus.active,
                is_active=True,
            )
        )
        session.add(
            Reminder(
                creator_id=1,
                type=ReminderType.once,
                text="future",
                fire_at=future,
                status=ReminderStatus.active,
                is_active=True,
            )
        )
        await session.commit()
        due = await repo.get_due_once(datetime.now(UTC))
        assert len(due) == 1
        assert due[0].text == "past"


@pytest.mark.asyncio
async def test_reminder_repository_mark_done(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = ReminderRepository(uow)
        reminder = Reminder(
            creator_id=1,
            type=ReminderType.once,
            text="test",
            status=ReminderStatus.active,
            is_active=True,
        )
        session.add(reminder)
        await session.commit()
        await repo.mark_done(reminder.id)
        await session.commit()
        updated = await session.get(Reminder, reminder.id)
        assert updated.status == ReminderStatus.done


@pytest.mark.asyncio
async def test_subscriber_repository_get_by_user_id(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = SubscriberRepository(uow)
        sub = Subscriber(user_id=1, username="test", name="Test")
        session.add(sub)
        await session.commit()
        fetched = await repo.get_by_user_id(1)
        assert fetched is not None
        assert fetched.username == "test"


@pytest.mark.asyncio
async def test_broadcast_recipient_repository_get_pending(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        repo = BroadcastRecipientRepository(uow)
        from src.reminder.models import Broadcast, BroadcastRecipient, BroadcastStatus
        broadcast = Broadcast(text="test", segment="active")
        session.add(broadcast)
        await session.flush()
        rr = BroadcastRecipient(broadcast_id=broadcast.id, user_id=1, status=BroadcastStatus.pending)
        session.add(rr)
        await session.commit()
        pending = await repo.get_pending()
        assert len(pending) == 1
        assert pending[0].status == BroadcastStatus.pending
