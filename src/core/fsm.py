from __future__ import annotations

from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from src.core.config import settings

try:
    storage: BaseStorage = RedisStorage.from_url(settings.redis_url, key_builder=DefaultKeyBuilder(prefix="fsm:reminder"))
except Exception:
    storage = MemoryStorage()
