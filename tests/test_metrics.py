from __future__ import annotations

from unittest.mock import AsyncMock, patch

from prometheus_client import Counter

from src.core.metrics import (
    BROADCAST_SENT,
    ERROR_HANDLER_ERRORS,
    REMINDERS_SENT,
    SCHEDULER_ERRORS,
    SCHEDULER_TICKS,
    WEBHOOK_REQUESTS,
    start_metrics,
    start_metrics_server,
)


def test_metrics_defined() -> None:
    assert isinstance(SCHEDULER_TICKS, Counter)
    assert isinstance(SCHEDULER_ERRORS, Counter)
    assert isinstance(REMINDERS_SENT, Counter)
    assert isinstance(BROADCAST_SENT, Counter)
    assert isinstance(ERROR_HANDLER_ERRORS, Counter)
    assert isinstance(WEBHOOK_REQUESTS, Counter)


async def test_start_metrics_server() -> None:
    with patch("src.core.metrics.web.AppRunner") as mock_runner_class:
        mock_runner = AsyncMock()
        mock_runner.setup = AsyncMock()
        mock_runner_class.return_value = mock_runner

        with patch("src.core.metrics.web.TCPSite") as mock_site_class:
            mock_site = AsyncMock()
            mock_site.start = AsyncMock()
            mock_site_class.return_value = mock_site

            runner = await start_metrics_server(9090)

            mock_runner_class.assert_called_once()
            mock_runner.setup.assert_awaited_once()
            mock_site_class.assert_called_once_with(mock_runner, "0.0.0.0", 9090)
            mock_site.start.assert_awaited_once()
            assert runner == mock_runner


def test_start_metrics_legacy() -> None:
    with patch("threading.Thread") as mock_thread:
        start_metrics(9090)
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
