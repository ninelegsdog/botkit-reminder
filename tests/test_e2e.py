from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, Message, Update, User

from src.core.bot_factory import create_bot
from src.reminder import register_routers


@pytest.mark.asyncio
async def test_start_command():
    bot = Bot(token="123:ABC")
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"ok": True, "result": {"message_id": 1}})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    
    with patch.object(bot.session, "make_request", new_callable=AsyncMock, return_value=mock_response):
        dp = Dispatcher(storage=MemoryStorage())
        app_state = create_bot()
        app_state.dp = dp
        app_state.bot = bot
        register_routers(app_state)
        message = Message(
            message_id=1,
            date=0,
            chat=Chat(id=1, type="private"),
            from_user=User(id=1, is_bot=False, first_name="Test"),
            text="/start",
        )
        update = Update(update_id=1, message=message)
        await dp.feed_update(bot, update)
        assert True
