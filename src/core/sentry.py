from __future__ import annotations

from typing import Any, Literal

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from src.core.config import settings


def init_sentry() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[
            LoggingIntegration(
                level=20,
                event_level=40,
            ),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production" if settings.telegram_bot_token else "development",
        release="botkit-reminder@0.2.0",
    )


def capture_exception(exc: BaseException, context: dict[str, Any] | None = None) -> None:
    with sentry_sdk.isolation_scope() as scope:
        if context:
            for key, value in context.items():
                scope.set_context(key, value)
        sentry_sdk.capture_exception(exc)


def capture_message(message: str, level: Literal["fatal", "critical", "error", "warning", "info", "debug"] = "info") -> None:
    sentry_sdk.capture_message(message, level=level)
