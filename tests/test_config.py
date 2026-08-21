from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.config import Settings


def test_settings_defaults() -> None:
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "123:ABC",
        "TELEGRAM_WEBHOOK_SECRET": "secret",
        "TELEGRAM_ADMIN_IDS": "1",
        "ADMIN_PASSWORD_HASH": "hash",
    }):
        settings = Settings()
        assert settings.database_url == "sqlite+aiosqlite:///./data/reminder.db"
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.tz == "Europe/Moscow"
        assert settings.scheduler_interval_seconds == 30
        assert settings.admin_ids == [1]


def test_settings_validation() -> None:
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "invalid",
        "TELEGRAM_WEBHOOK_SECRET": "change-me",
        "TELEGRAM_ADMIN_IDS": "",
        "ADMIN_PASSWORD_HASH": "",
        "SCHEDULER_INTERVAL_SECONDS": "0",
    }), pytest.raises(RuntimeError):
        s = Settings()
        s.validate_on_startup()
