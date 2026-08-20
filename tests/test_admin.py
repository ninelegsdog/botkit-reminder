from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from src.reminder.models import Base
from src.admin.service import AdminService


@pytest.fixture
async def session_factory(tmp_path):
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


@pytest.mark.asyncio
async def test_admin_stats(session_factory):
    async with session_factory() as session:
        service = AdminService(session)
        stats = await service.stats()
        assert "subscribers" in stats
        assert "reminders" in stats
