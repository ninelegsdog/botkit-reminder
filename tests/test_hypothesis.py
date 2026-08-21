from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.uow import UnitOfWork
from src.reminder.models import ReminderStatus, ReminderType
from src.reminder.service import ReminderService


@pytest.fixture
async def session_factory(tmp_path: Any) -> Any:
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    user_id=st.integers(min_value=1, max_value=10**9),
    text=st.text(min_size=1, max_size=200),
)
async def test_create_reminder_property(session_factory: Any, user_id: int, text: str) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = ReminderService(uow)
        fire_at = datetime.now(UTC) + timedelta(hours=1)
        reminder = await service.create_reminder(user_id, ReminderType.once, text, fire_at=fire_at)
        assert reminder.id is not None
        assert reminder.creator_id == user_id
        assert reminder.text == text
        assert reminder.type == ReminderType.once
        assert reminder.status == ReminderStatus.active


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    offset_minutes=st.integers(min_value=-60, max_value=60),
)
async def test_get_due_reminders_property(session_factory: Any, offset_minutes: int) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = ReminderService(uow)
        now = datetime.now(UTC)
        past = now - timedelta(minutes=120)
        future = now + timedelta(hours=2)
        await service.create_reminder(1, ReminderType.once, "past", fire_at=past)
        await service.create_reminder(1, ReminderType.once, "future", fire_at=future)
        await session.commit()
        due = await service.get_due_reminders(now + timedelta(minutes=offset_minutes))
        texts = {r.text for r in due}
        assert "past" in texts
        assert "future" not in texts
