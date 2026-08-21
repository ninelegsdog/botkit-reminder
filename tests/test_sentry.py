from __future__ import annotations

from unittest.mock import patch

from src.core.sentry import capture_exception, capture_message, init_sentry


def test_init_sentry_without_dsn() -> None:
    with patch("src.core.sentry.settings") as mock_settings:
        mock_settings.sentry_dsn = ""
        with patch("sentry_sdk.init") as mock_init:
            init_sentry()
            mock_init.assert_not_called()


def test_init_sentry_with_dsn() -> None:
    with patch("src.core.sentry.settings") as mock_settings:
        mock_settings.sentry_dsn = "https://test@sentry.io/123"
        mock_settings.telegram_bot_token = "123:ABC"
        with patch("sentry_sdk.init") as mock_init:
            init_sentry()
            assert mock_init.called


def test_capture_exception() -> None:
    with patch("sentry_sdk.isolation_scope") as mock_scope:
        mock_scope.return_value.__enter__ = lambda self, *args, **kwargs: self
        mock_scope.return_value.__exit__ = lambda self, *args, **kwargs: False
        with patch("sentry_sdk.capture_exception") as mock_capture:
            exc = RuntimeError("test error")
            capture_exception(exc, {"user_id": 1})
            mock_capture.assert_called_once()


def test_capture_message() -> None:
    with patch("sentry_sdk.capture_message") as mock_capture:
        capture_message("test message", level="warning")
        mock_capture.assert_called_once_with("test message", level="warning")
