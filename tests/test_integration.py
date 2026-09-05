"""Integration tests with testcontainers (PostgreSQL, Redis)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.core.database import Base
from src.reminder.models import Reminder, Subscriber


@pytest.fixture
async def postgres_session_factory(postgres_url: str) -> Any:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_repository_crud(postgres_session_factory: Any) -> None:
    from src.core.uow import UnitOfWork
    from src.reminder.models import ReminderStatus, ReminderType
    from src.reminder.repositories import ReminderRepository, SubscriberRepository

    async with postgres_session_factory() as session:
        uow = UnitOfWork(session)
        reminder_repo = ReminderRepository(uow)
        sub_repo = SubscriberRepository(uow)

        # Create subscriber with explicit naive datetime
        sub = Subscriber(user_id=1, username="test", name="Test User")
        sub.subscribed_at = datetime.now(UTC).replace(tzinfo=None)
        session.add(sub)
        await session.commit()

        fetched_sub = await sub_repo.get_by_user_id(1)
        assert fetched_sub is not None
        assert fetched_sub.username == "test"

        # Use timezone-naive datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
        fire_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        now_naive = datetime.now(UTC).replace(tzinfo=None)
        reminder = Reminder(
            creator_id=1,
            type=ReminderType.once,
            text="Integration test",
            fire_at=fire_at,
            status=ReminderStatus.active,
            is_active=True,
            created_at=now_naive,
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_connection(redis_client) -> None:
    """Test Redis connection using testcontainers fixture."""
    pong = await redis_client.ping()
    assert pong is True
