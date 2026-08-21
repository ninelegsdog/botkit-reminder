from __future__ import annotations

from typing import Any

from src.core.config import settings


class Cache:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        self._cache[key] = value

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def clear(self) -> None:
        self._cache.clear()


cache = Cache()


def get_redis_client() -> Any | None:
    if not settings.redis_url or settings.redis_url == "redis://localhost:6379/0":
        return None
    try:
        import redis.asyncio as aioredis
        return aioredis.from_url(settings.redis_url)
    except ImportError:
        return None
