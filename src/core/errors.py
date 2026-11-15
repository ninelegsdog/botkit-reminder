from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.types import ErrorEvent, TelegramObject

from src.core.metrics import ERRORS_TOTAL

logger = logging.getLogger(__name__)

_ERROR_TYPES = ("retry_after", "network", "unhandled", "domain")


def init_error_metrics() -> None:
    for error_type in _ERROR_TYPES:
        ERRORS_TOTAL.labels(error_type=error_type).inc(0)


async def _handle_retry_after(event: TelegramObject, exc: TelegramRetryAfter) -> None:
    await asyncio.sleep(exc.retry_after)
    if hasattr(event, "message") and event.message:
        with suppress(Exception):
            await event.message.answer(
                f"⚠️ Telegram flood control. Повторите через {exc.retry_after} сек."
            )


async def default_error_handler(event: TelegramObject, exc: Exception) -> None:
    if isinstance(exc, TelegramRetryAfter):
        ERRORS_TOTAL.labels(error_type="retry_after").inc()
        logger.warning("TelegramRetryAfter: %s", exc)
        await _handle_retry_after(event, exc)
        return
    if isinstance(exc, TelegramNetworkError):
        ERRORS_TOTAL.labels(error_type="network").inc()
        logger.warning("TelegramNetworkError: %s", exc)
        return
    ERRORS_TOTAL.labels(error_type="unhandled").inc()
    logger.critical("Unhandled error: %s", exc)


def register_error_handler(dp: Any) -> None:
    # Ensure the error series exist before any error can fire.
    init_error_metrics()

    @dp.error()  # type: ignore[untyped-decorator]
    async def error_handler(event: ErrorEvent) -> None:
        await default_error_handler(event, event.exception)


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
