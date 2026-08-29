from __future__ import annotations

import hashlib
import hmac
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from aiogram import types

from src.core.config import settings

F = TypeVar("F", bound=Callable[..., Awaitable[None]])


def verify_password(password: str) -> bool:
    expected = settings.admin_password_hash if settings.admin_password else hashlib.sha256(b"admin").hexdigest()
    return hmac.compare_digest(
        hashlib.sha256(password.encode()).hexdigest(),
        expected,
    )


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


class AdminGate:
    def __init__(self) -> None:
        self._authorized: set[int] = set()

    def login(self, user_id: int) -> None:
        self._authorized.add(user_id)

    def logout(self, user_id: int) -> None:
        self._authorized.discard(user_id)

    def is_authorized(self, user_id: int) -> bool:
        return user_id in self._authorized


admin_gate = AdminGate()


def admin_only(handler: F) -> F:  # noqa: UP047
    @wraps(handler)
    async def wrapper(event: types.TelegramObject, *args: object, **kwargs: object) -> None:
        user = getattr(event, "from_user", None)
        if not user or not admin_gate.is_authorized(user.id):
            return
        return await handler(event, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
