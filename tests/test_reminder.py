from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.uow import UnitOfWork
from src.reminder.models import ReminderType
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
async def test_create_reminder(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = ReminderService(uow)
        fire_at = datetime.now(UTC) + timedelta(hours=1)
        reminder = await service.create_reminder(1, ReminderType.once, "Test", fire_at=fire_at)
        assert reminder.id is not None
        assert reminder.text == "Test"


@pytest.mark.asyncio
async def test_subscribe(session_factory: Any) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = SubscriptionService(uow)
        sub = await service.subscribe(1, "user", "Name")
        assert sub.is_active is True
        await service.unsubscribe(1)
        assert sub.is_active is False
