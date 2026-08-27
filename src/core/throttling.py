from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis
from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis_url: str, rate_limit: float = 0.5) -> None:
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[..., Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, **data)

        key = f"throttle:{handler.__name__}:{user.id}"
        now = time.time()
        try:
            last = await self._redis.get(key)
            if last and now - float(last) < self._rate_limit:
                return
            await self._redis.set(key, str(now), ex=int(self._rate_limit * 2))
        except Exception:
            pass  # Don't fail on Redis errors
        return await handler(event, **data)
