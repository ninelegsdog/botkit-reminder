from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    bot_token: str = ""
    admin_password: str = ""
    redis_url: str = "redis://localhost:6379/0"
    db_path: str = "data/reminder.db"
    log_level: str = "INFO"
    scheduler_interval: int = 30

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            admin_password=os.getenv("ADMIN_PASSWORD", ""),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            db_path=os.getenv("DB_PATH", "data/reminder.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            scheduler_interval=int(os.getenv("SCHEDULER_INTERVAL", "30")),
        )


@dataclass
class State:
    config: Config = field(default_factory=Config.from_env)
