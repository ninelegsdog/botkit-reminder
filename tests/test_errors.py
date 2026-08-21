from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from aiogram.methods.base import TelegramMethod
from aiogram.types import TelegramObject

from src.core.errors import default_error_handler, register_error_handler


@pytest.mark.asyncio
async def test_retry_after_handler() -> None:
    event = MagicMock(spec=TelegramObject)
    event.message = MagicMock()
    event.message.answer = AsyncMock()
    method = MagicMock(spec=TelegramMethod)
    exc = TelegramRetryAfter(method=method, message="flood", retry_after=1)
    with patch("src.core.errors.logger") as mock_logger:
        await default_error_handler(event, exc)
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_network_error_handler() -> None:
    event = MagicMock(spec=TelegramObject)
    method = MagicMock(spec=TelegramMethod)
    exc = TelegramNetworkError(method=method, message="network error")
    with patch("src.core.errors.logger") as mock_logger:
        await default_error_handler(event, exc)
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_unhandled_error_handler() -> None:
    event = MagicMock(spec=TelegramObject)
    exc = RuntimeError("unhandled")
    with patch("src.core.errors.logger") as mock_logger:
        await default_error_handler(event, exc)
        mock_logger.critical.assert_called_once()


def test_register_error_handler() -> None:
    dp = MagicMock()
    register_error_handler(dp)
    assert dp.error.called
