from __future__ import annotations

import json
from contextlib import suppress
from typing import Any

from src.core.config import settings


class Cache:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._redis: Any = None

    async def init(self) -> None:
        if settings.redis_url and settings.redis_url != "redis://localhost:6379/0":
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(settings.redis_url)
            except ImportError:
                pass

    async def get(self, key: str) -> Any | None:
        if self._redis:
            try:
                value = await self._redis.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception:
                pass
        return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if self._redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(value))
                return
            except Exception:
                pass
        self._cache[key] = value

    async def delete(self, key: str) -> None:
        if self._redis:
            with suppress(Exception):
                await self._redis.delete(key)
        self._cache.pop(key, None)

    async def clear(self) -> None:
        if self._redis:
            with suppress(Exception):
                await self._redis.flushdb()
        self._cache.clear()


cache = Cache()
