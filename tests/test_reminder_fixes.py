from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.auth import admin_gate
from src.core.bot_factory import create_bot
from src.core.database import Base
from src.core.uow import UnitOfWork
from src.reminder import register_routers
from src.reminder.models import ReminderType
from src.reminder.scheduler import Scheduler
from src.reminder.service import ReminderService


@pytest.fixture
def app_state() -> Any:
    state = create_bot()
    state.dp = Dispatcher(storage=MemoryStorage())
    return state


@pytest.fixture
def mock_uow() -> Any:
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    session.flush = AsyncMock()
    session.add = MagicMock()
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.session = session
    return uow


@pytest.fixture
async def session_factory(tmp_path: Any) -> Any:
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def _msg(text: str, mid: int) -> Message:
    return Message(
        message_id=mid,
        date=datetime.now(),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="X"),
        text=text,
    )


def _cb(data: str) -> CallbackQuery:
    return CallbackQuery(
        id="1",
        from_user=User(id=1, is_bot=False, first_name="X"),
        chat_instance="ci",
        message=_msg("x", 0),
        data=data,
    )


# --- Bug 1: broadcast must require admin ---
@pytest.mark.asyncio
async def test_broadcast_blocked_for_non_admin(app_state: Any, mock_uow: Any) -> None:
    admin_gate.logout(1)
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=AsyncMock(status=200)) as mr, \
         patch("src.reminder.handlers.UnitOfWork", return_value=mock_uow):
        await app_state.dp.feed_update(bot, Update(update_id=1, message=_msg("📣 Рассылки", 1)))
    assert mr.call_count == 0
    assert not mock_uow.session.add.called


@pytest.mark.asyncio
async def test_broadcast_works_for_admin(app_state: Any, mock_uow: Any) -> None:
    admin_gate.login(1)
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=AsyncMock(status=200)), \
         patch("src.reminder.handlers.UnitOfWork", return_value=mock_uow):
        await app_state.dp.feed_update(bot, Update(update_id=1, message=_msg("📣 Рассылка", 1)))
        await app_state.dp.feed_update(bot, Update(update_id=2, message=_msg("Hello subscribers", 2)))
    assert mock_uow.session.add.called
    added = mock_uow.session.add.call_args.args[0]
    assert added.text == "Hello subscribers"


# --- Bug 2: recurring reminders must not spam ---
@pytest.mark.asyncio
async def test_recurring_sent_only_at_match_time(session_factory: Any) -> None:
    sent: list[tuple[int, str]] = []

    async def cb(uid: int, text: str) -> None:
        sent.append((uid, text))

    scheduler = Scheduler(session_factory, cb)
    now = datetime.now(UTC)
    async with session_factory() as session:
        svc = ReminderService(UnitOfWork(session))
        fire = now.replace(year=2000, month=1, day=1)
        await svc.create_reminder(1, ReminderType.recurring, "Daily", fire_at=fire, cron_day=str(now.weekday()))
        await session.commit()

    await scheduler._tick()
    assert len(sent) == 1
    await scheduler._tick()
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_recurring_not_sent_off_time(session_factory: Any) -> None:
    sent: list[tuple[int, str]] = []

    async def cb(uid: int, text: str) -> None:
        sent.append((uid, text))

    scheduler = Scheduler(session_factory, cb)
    now = datetime.now(UTC)
    async with session_factory() as session:
        svc = ReminderService(UnitOfWork(session))
        off_hour = (now.hour + 1) % 24
        fire = now.replace(year=2000, month=1, day=1, hour=off_hour, minute=now.minute)
        await svc.create_reminder(1, ReminderType.recurring, "Daily", fire_at=fire, cron_day=str(now.weekday()))
        await session.commit()

    await scheduler._tick()
    assert len(sent) == 0


# --- Bug 3: "Add" flow must collect reminder text ---
@pytest.mark.asyncio
async def test_add_once_flow_creates_reminder(app_state: Any, mock_uow: Any) -> None:
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=AsyncMock(status=200)), \
         patch("src.reminder.handlers.UnitOfWork", return_value=mock_uow):
        await app_state.dp.feed_update(bot, Update(update_id=1, message=_msg("➕ Добавить", 1)))
        await app_state.dp.feed_update(bot, Update(update_id=2, callback_query=_cb("rem:type:once")))
        await app_state.dp.feed_update(bot, Update(update_id=3, message=_msg("Купить молоко", 2)))
        await app_state.dp.feed_update(bot, Update(update_id=4, message=_msg("31.12.2030", 3)))
        await app_state.dp.feed_update(bot, Update(update_id=5, message=_msg("09:30", 4)))
    assert mock_uow.session.add.called
    reminder = mock_uow.session.add.call_args.args[0]
    assert reminder.text == "Купить молоко"
    assert reminder.type == ReminderType.once
    assert reminder.fire_at is not None
    assert reminder.fire_at.hour == 9 and reminder.fire_at.minute == 30


@pytest.mark.asyncio
async def test_add_recurring_flow_creates_reminder(app_state: Any, mock_uow: Any) -> None:
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=AsyncMock(status=200)), \
         patch("src.reminder.handlers.UnitOfWork", return_value=mock_uow):
        await app_state.dp.feed_update(bot, Update(update_id=1, message=_msg("➕ Добавить", 1)))
        await app_state.dp.feed_update(bot, Update(update_id=2, callback_query=_cb("rem:type:recurring")))
        await app_state.dp.feed_update(bot, Update(update_id=3, callback_query=_cb("rem:day:2")))
        await app_state.dp.feed_update(bot, Update(update_id=4, message=_msg("Позвонить маме", 2)))
        await app_state.dp.feed_update(bot, Update(update_id=5, message=_msg("18:00", 3)))
    assert mock_uow.session.add.called
    reminder = mock_uow.session.add.call_args.args[0]
    assert reminder.text == "Позвонить маме"
    assert reminder.type == ReminderType.recurring
    assert reminder.cron_day == "2"
    assert reminder.fire_at is not None
    assert reminder.fire_at.hour == 18 and reminder.fire_at.minute == 0
