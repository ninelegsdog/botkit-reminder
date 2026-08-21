from __future__ import annotations

from unittest.mock import patch

from prometheus_client import Counter

from src.core.metrics import (
    BROADCAST_SENT,
    ERROR_HANDLER_ERRORS,
    REMINDERS_SENT,
    SCHEDULER_ERRORS,
    SCHEDULER_TICKS,
    WEBHOOK_REQUESTS,
    start_metrics,
)


def test_metrics_defined() -> None:
    assert isinstance(SCHEDULER_TICKS, Counter)
    assert isinstance(SCHEDULER_ERRORS, Counter)
    assert isinstance(REMINDERS_SENT, Counter)
    assert isinstance(BROADCAST_SENT, Counter)
    assert isinstance(ERROR_HANDLER_ERRORS, Counter)
    assert isinstance(WEBHOOK_REQUESTS, Counter)


def test_start_metrics() -> None:
    with patch("src.core.metrics.start_http_server") as mock_start:
        start_metrics(9090)
        mock_start.assert_called_once_with(9090)
