## Redis migration: shared Redis with DB sharding on port 6380
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    telegram_bot_token: str
    telegram_webhook_secret: str
    webhook_secret: str = ""
    webhook_url: str = ""
    webhook_cert_path: str = ""
    admin_ids: str
    admin_password: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/reminder.db"
    redis_url: str = "redis://127.0.0.1:6380/8"

    tz: str = "Europe/Moscow"

    scheduler_interval_seconds: int = 30

    metrics_port: int = 9090

    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    telegram_stars_provider_enabled: bool = True

    log_level: str = "INFO"

    sentry_dsn: str = ""

    @property
    def admin_ids_list(self) -> list[int]:
        result: list[int] = []
        for token in self.admin_ids.split(","):
            token = token.strip()
            if not token:
                continue
            try:
                result.append(int(token))
            except ValueError:
                logging.warning("Invalid admin id ignored: %r", token)
        return result

    @property
    def admin_password_hash(self) -> str:
        return hashlib.sha256(self.admin_password.encode("utf-8")).hexdigest()

    def validate_on_startup(self) -> None:
        if not self.telegram_bot_token or ":" not in self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is invalid")
        if self.telegram_webhook_secret == "change-me":
            raise RuntimeError("TELEGRAM_WEBHOOK_SECRET must be changed from default")
        if not self.admin_ids:
            raise RuntimeError("TELEGRAM_ADMIN_IDS is empty")
        if not self.admin_password:
            raise RuntimeError("ADMIN_PASSWORD is not set")
        if self.scheduler_interval_seconds <= 0:
            raise RuntimeError("SCHEDULER_INTERVAL_SECONDS must be positive")


settings = Settings()

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
