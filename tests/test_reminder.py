from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from src.reminder.models import Base, Reminder, ReminderRecipient, ReminderType, ReminderStatus, Subscriber, Broadcast
from src.reminder.service import ReminderService, SubscriptionService


@pytest.fixture
async def session_factory(tmp_path):
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.asyncio
async def test_create_reminder(session_factory):
    async with session_factory() as session:
        service = ReminderService(session, None)
        fire_at = datetime.utcnow() + timedelta(hours=1)
        reminder = await service.create_reminder(1, ReminderType.once, "Test", fire_at=fire_at)
        assert reminder.id is not None
        assert reminder.text == "Test"


@pytest.mark.asyncio
async def test_subscribe(session_factory):
    async with session_factory() as session:
        service = SubscriptionService(session)
        sub = await service.subscribe(1, "user", "Name")
        assert sub.is_active is True
        await service.unsubscribe(1)
        assert sub.is_active is False
