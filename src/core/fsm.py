from __future__ import annotations

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings

try:
    storage = RedisStorage.from_url(settings.redis_url)
except Exception:
    storage = MemoryStorage()
