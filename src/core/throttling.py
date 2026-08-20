from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict

from aiogram import types

_THROTTLE: Dict[str, Dict[int, float]] = defaultdict(dict)


class ThrottlingMiddleware:
    async def __call__(self, handler, event: types.TelegramObject, data: dict) -> None:
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
