from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings
from src.core.database import Database


class AppState:
    def __init__(self) -> None:
        self.bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode="HTML"),
        )
        self.storage: BaseStorage = MemoryStorage()
        if settings.redis_url:
            try:
                self.storage = RedisStorage.from_url(settings.redis_url)
            except Exception:
                self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.db = Database(settings.database_url)


state = AppState()


def create_bot() -> AppState:
    return state
