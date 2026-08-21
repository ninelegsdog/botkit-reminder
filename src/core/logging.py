from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from src.core.config import settings


def _add_service(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["service"] = "botkit-reminder"
    return event_dict


def _add_environment(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict["environment"] = "production" if settings.telegram_bot_token else "development"
    return event_dict


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            _add_service,  # type: ignore[list-item]
            _add_environment,  # type: ignore[list-item]
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
