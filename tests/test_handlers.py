from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

from src.core.bot_factory import create_bot
from src.reminder import register_routers


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
    session.commit = AsyncMock()
    session.add = MagicMock()

    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.session = session
    return uow


@pytest.mark.asyncio
async def test_add_reminder_shows_types(app_state: Any, mock_uow: Any) -> None:
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="Test"),
        text="➕ Добавить",
    )
    update = Update(update_id=1, message=message)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=mock_response), \
         patch("src.reminder.handlers.UnitOfWork", return_value=mock_uow):
        await app_state.dp.feed_update(bot, update)
        assert True


@pytest.mark.asyncio
async def test_subscribe_flow(app_state: Any, mock_uow: Any) -> None:
    bot = Bot(token="123:ABC")
    app_state.bot = bot
    register_routers(app_state)
    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="Test"),
        text="🔔 Подписаться",
    )
    update = Update(update_id=1, message=message)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=mock_response), \
         patch("src.reminder.handlers.UnitOfWork", return_value=mock_uow):
        await app_state.dp.feed_update(bot, update)
        assert True
