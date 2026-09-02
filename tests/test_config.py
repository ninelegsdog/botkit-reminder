from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.config import Settings


def test_settings_defaults() -> None:
    import os

    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "123:ABC",
        "TELEGRAM_WEBHOOK_SECRET": "secret",
        "ADMIN_IDS": "1",
        "ADMIN_PASSWORD_HASH": "hash",
    }):
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("REDIS_URL", None)
        settings = Settings(_env_file=None)
        assert settings.database_url == "sqlite+aiosqlite:///./data/reminder.db"
        assert settings.redis_url == "redis://127.0.0.1:6380/8"
        assert settings.tz == "Europe/Moscow"
        assert settings.scheduler_interval_seconds == 30
        assert settings.admin_ids_list == [1]


def test_settings_validation() -> None:
    with patch.dict("os.environ", {
        "TELEGRAM_BOT_TOKEN": "invalid",
        "TELEGRAM_WEBHOOK_SECRET": "change-me",
        "ADMIN_IDS": "1",
        "ADMIN_PASSWORD_HASH": "x",
        "SCHEDULER_INTERVAL_SECONDS": "0",
    }), pytest.raises(RuntimeError):
        s = Settings(_env_file=None)
        s.validate_on_startup()
