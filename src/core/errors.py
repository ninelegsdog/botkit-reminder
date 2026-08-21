from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


async def _handle_retry_after(event: TelegramObject, exc: TelegramRetryAfter) -> None:
    await asyncio.sleep(exc.retry_after)
    if hasattr(event, "message") and event.message:
        with suppress(Exception):
            await event.message.answer(
                f"⚠️ Telegram flood control. Повторите через {exc.retry_after} сек."
            )


async def default_error_handler(event: TelegramObject, exc: Exception) -> None:
    if isinstance(exc, TelegramRetryAfter):
        logger.warning("TelegramRetryAfter: %s", exc)
        await _handle_retry_after(event, exc)
        return
    if isinstance(exc, TelegramNetworkError):
        logger.warning("TelegramNetworkError: %s", exc)
        return
    logger.critical("Unhandled error: %s", exc, exc_info=True)


def register_error_handler(dp: Any) -> None:
    @dp.error()  # type: ignore[untyped-decorator]
    async def error_handler(event: TelegramObject, exception: Exception) -> None:
        await default_error_handler(event, exception)


class RetryMiddleware:
    def __init__(self, max_retries: int = 3, delay: float = 1.0) -> None:
        self._max_retries = max_retries
        self._delay = delay

    async def __call__(
        self,
        handler: Callable[..., Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        retries = 0
        while True:
            try:
                return await handler(event, data)
            except TelegramRetryAfter as exc:
                logger.warning("RetryAfter in handler: %s", exc)
                await _handle_retry_after(event, exc)
                retries += 1
                if retries >= self._max_retries:
                    raise
            except TelegramNetworkError as exc:
                logger.warning("NetworkError in handler: %s", exc)
                retries += 1
                if retries >= self._max_retries:
                    raise
                import asyncio
                await asyncio.sleep(self._delay * retries)
