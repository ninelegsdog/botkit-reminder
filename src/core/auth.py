from __future__ import annotations

import hashlib
import hmac
import time
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
    return user_id in settings.admin_ids_list


class AdminGate:
    """Tracks who is authorised, and how many wrong passwords each user has tried.

    This gate recorded nothing about failures, so the admin surface accepted unlimited
    guesses: the class looked like protection and provided none. It now keeps a
    per-user attempt list and `is_throttled` reports when the window is exhausted.

    The bot calls `record_failure` on a wrong password and checks `is_throttled` before
    comparing, so the limit is actually enforced. The window and cap match the shared
    `botkit_core.admin.AdminGate` (5 attempts / 300 s) rather than being invented here.
    """

    _WINDOW = 300.0
    _MAX_ATTEMPTS = 5

    def __init__(self) -> None:
        self._authorized: set[int] = set()
        self._attempts: dict[int, list[float]] = {}

    def login(self, user_id: int) -> None:
        self._authorized.add(user_id)
        self._attempts.pop(user_id, None)

    def logout(self, user_id: int) -> None:
        self._authorized.discard(user_id)

    def is_authorized(self, user_id: int) -> bool:
        return user_id in self._authorized

    def record_failure(self, user_id: int) -> None:
        """Note a wrong password for this user."""
        now = time.time()
        attempts = self._attempts.setdefault(user_id, [])
        attempts[:] = [t for t in attempts if now - t < self._WINDOW]
        attempts.append(now)

    def is_throttled(self, user_id: int) -> bool:
        """True while this user is inside the throttle window after too many failures."""
        now = time.time()
        attempts = self._attempts.get(user_id, [])
        attempts[:] = [t for t in attempts if now - t < self._WINDOW]
        return len(attempts) >= self._MAX_ATTEMPTS


admin_gate = AdminGate()


def admin_only(handler: F) -> F:  # noqa: UP047
    @wraps(handler)
    async def wrapper(event: types.TelegramObject, *args: object, **kwargs: object) -> None:
        user = getattr(event, "from_user", None)
        if not user or not admin_gate.is_authorized(user.id):
            return
        return await handler(event, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
