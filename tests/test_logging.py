from __future__ import annotations

from unittest.mock import patch


def test_configure_logging() -> None:
    with patch("src.core.logging.structlog.configure") as mock_configure:
        from src.core.logging import configure_logging
        configure_logging()
        mock_configure.assert_called_once()
        call_kwargs = mock_configure.call_args[1]
        assert "processors" in call_kwargs
        assert "context_class" in call_kwargs
        assert "logger_factory" in call_kwargs
        assert "cache_logger_on_first_use" in call_kwargs


def test_configure_logging_sets_level() -> None:
    with patch("src.core.logging.structlog.configure") as mock_configure:
        from src.core.logging import configure_logging
        configure_logging()
        mock_configure.assert_called_once()
