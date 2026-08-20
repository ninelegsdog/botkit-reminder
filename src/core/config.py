from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str
    telegram_webhook_secret: str
    telegram_admin_ids: str
    admin_password_hash: str

    database_url: str = "sqlite+aiosqlite:///./data/reminder.db"
    redis_url: str = "redis://localhost:6379/0"

    tz: str = "Europe/Moscow"

    scheduler_interval_seconds: int = 30

    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    telegram_stars_provider_enabled: bool = True

    log_level: str = "INFO"

    @property
    def admin_ids(self) -> list[int]:
        return [int(x.strip()) for x in self.telegram_admin_ids.split(",") if x.strip()]


settings = Settings()

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
