"""Regression: ThrottlingMiddleware must call the next handler with the aiogram 3
signature ``handler(event, data)``, never the aiogram 2 ``handler(event, **data)``.

Context: the aiogram 2 form shipped to production and made every text update raise
``TypeError: ... got an unexpected keyword argument 'dispatcher'``. aiogram 3 wraps the
handler as ``handler_wrapper(event, kwargs)`` (see ``MiddlewareManager.wrap_middlewares``),
so passing context as keyword arguments can never work.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core.throttling import ThrottlingMiddleware


class _FakeRedis:
    def __init__(self, last: str | None = None, fail: bool = False) -> None:
        self._last = last
        self._fail = fail
        self.set_calls: list[tuple[str, str, int | None]] = []

    async def get(self, key: str) -> str | None:
        if self._fail:
            raise RuntimeError("redis down")
        return self._last

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self._fail:
            raise RuntimeError("redis down")
        self.set_calls.append((key, value, ex))


class _FakeUser:
    id = 7


class _FakeEvent:
    from_user = _FakeUser()


class _NoUserEvent:
    from_user = None


def _middleware(fake: _FakeRedis) -> ThrottlingMiddleware:
    mw = ThrottlingMiddleware("redis://localhost:6379/0")
    mw._redis = fake  # type: ignore[assignment]
    return mw


def test_context_is_passed_as_positional_dict() -> None:
    """With the aiogram 2 form this test fails: **data becomes unexpected kwargs."""
    mw = _middleware(_FakeRedis())
    seen: dict[str, Any] = {}

    async def handler(event: object, data: dict[str, Any]) -> dict[str, Any]:
        seen.update(data)
        return data

    context = {"dispatcher": object(), "bot": object()}
    result = asyncio.run(mw(handler, _FakeEvent(), context))
    assert result is context
    assert set(seen) == {"dispatcher", "bot"}


def test_without_user_skips_throttling_but_still_calls_handler() -> None:
    fake = _FakeRedis()
    mw = _middleware(fake)
    called = False

    async def handler(event: object, data: dict[str, Any]) -> str:
        nonlocal called
        called = True
        return "ok"

    assert asyncio.run(mw(handler, _NoUserEvent(), {})) == "ok"
    assert called
    assert fake.set_calls == []


def test_repeat_within_limit_is_dropped() -> None:
    fake = _FakeRedis(last=str(time.time()))
    mw = _middleware(fake)
    called = False

    async def handler(event: object, data: dict[str, Any]) -> str:
        nonlocal called
        called = True
        return "ok"

    assert asyncio.run(mw(handler, _FakeEvent(), {})) is None
    assert not called


def test_redis_failure_does_not_block_handler() -> None:
    mw = _middleware(_FakeRedis(fail=True))

    async def handler(event: object, data: dict[str, Any]) -> str:
        return "ok"

    assert asyncio.run(mw(handler, _FakeEvent(), {})) == "ok"
