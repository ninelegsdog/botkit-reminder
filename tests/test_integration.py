from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.uow import UnitOfWork
from src.reminder.models import Reminder, ReminderStatus, ReminderType, Subscriber
from src.reminder.repositories import ReminderRepository, SubscriberRepository


def get_postgres_url() -> str | None:
    import os
    url = os.getenv("DATABASE_URL", "")
    if "postgresql" in url:
        return url
    return None


@pytest.fixture
async def postgres_session_factory() -> Any:
    url = get_postgres_url()
    if not url:
        pytest.skip("PostgreSQL not available")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.integration_test
@pytest.mark.asyncio
async def test_postgres_repository_crud(postgres_session_factory: Any) -> None:
    async with postgres_session_factory() as session:
        uow = UnitOfWork(session)
        reminder_repo = ReminderRepository(uow)
        sub_repo = SubscriberRepository(uow)

        sub = Subscriber(user_id=1, username="test", name="Test User")
        session.add(sub)
        await session.commit()

        fetched_sub = await sub_repo.get_by_user_id(1)
        assert fetched_sub is not None
        assert fetched_sub.username == "test"

        reminder = Reminder(
            creator_id=1,
            type=ReminderType.once,
            text="Integration test",
            fire_at=datetime.now() + timedelta(hours=1),
            status=ReminderStatus.active,
            is_active=True,
        )
        session.add(reminder)
        await session.commit()

        fetched = await reminder_repo.get_by_id(reminder.id)
        assert fetched is not None
        assert fetched.text == "Integration test"

        await reminder_repo.mark_done(reminder.id)
        await session.commit()
        updated = await session.get(Reminder, reminder.id)
        assert updated.status == ReminderStatus.done


@pytest.mark.integration_test
@pytest.mark.asyncio
async def test_redis_connection() -> None:
    import os
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        pytest.skip("Redis not available")
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url)
        pong = await client.ping()
        assert pong is True
        await client.aclose()
    except ImportError:
        pytest.skip("redis package not installed")
