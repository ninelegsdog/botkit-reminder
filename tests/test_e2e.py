from __future__ import annotations

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Message, User, Chat
from aiogram.fsm.storage.memory import MemoryStorage

from src.core.bot_factory import create_bot
from src.reminder import register_routers


@pytest.mark.asyncio
async def test_start_command():
    bot = Bot(token="123:ABC")
    dp = Dispatcher(storage=MemoryStorage())
    register_routers(dp)
    message = Message(
        message_id=1,
        date=0,
        chat=Chat(id=1, type="private"),
        from_user=User(id=1, is_bot=False, first_name="Test"),
        text="/start",
    )
    await dp.feed_update(bot, {"message": message.model_dump()})
    assert True
