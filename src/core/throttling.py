from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

_THROTTLE: dict[str, dict[int, float]] = defaultdict(dict)


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[..., Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, **data)

        key = f"{handler.__name__}:{user.id}"
        now = time.time()
        last = _THROTTLE[key].get(user.id, 0)
        if now - last < 0.5:
            return
        _THROTTLE[key][user.id] = now
        return await handler(event, **data)
