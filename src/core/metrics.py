from __future__ import annotations

from prometheus_client import Counter, Gauge, generate_latest, start_http_server
from aiogram import types

MESSAGES_TOTAL = Counter("bot_messages_total", "Total messages", ["handler", "status"])
ACTIVE_USERS = Gauge("bot_active_users", "Active users", ["period"])


async def metrics_handler(event: types.Message) -> None:
    pass


def start_metrics(port: int = 9090) -> None:
    start_http_server(port)
