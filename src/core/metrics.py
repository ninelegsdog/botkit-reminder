from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

logger = logging.getLogger(__name__)

UPDATES_TOTAL = Counter(
    "bot_updates_total",
    "Total updates received from Telegram",
    ["type"],
)

SCHEDULER_TICKS = Counter(
    "scheduler_ticks_total",
    "Scheduler ticks",
    ["status"],
)
SCHEDULER_ERRORS = Counter(
    "scheduler_errors_total",
    "Scheduler tick errors",
    ["error_type"],
)
REMINDERS_SENT = Counter(
    "reminders_sent_total",
    "Reminders sent",
    ["type"],
)
BROADCAST_SENT = Counter(
    "broadcast_sent_total",
    "Broadcast messages sent",
    ["status"],
)
ERROR_HANDLER_ERRORS = Counter(
    "error_handler_errors_total",
    "Errors caught by global handler",
    ["error_type"],
)
WEBHOOK_REQUESTS = Counter(
    "webhook_requests_total",
    "Webhook requests",
    ["status"],
)


class UpdatesMiddleware:
    """Counts every incoming update."""

    async def __call__(
        self,
        handler: Any,
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        UPDATES_TOTAL.labels(type=type(event).__name__.lower()).inc()
        return await handler(event, data)


@dataclass
class Metrics:
    _start: float = field(default_factory=time.time)
    messages_processed: int = 0
    reminders_sent: int = 0
    errors: int = 0

    def inc_messages(self) -> None:
        self.messages_processed += 1

    def inc_reminders(self) -> None:
        self.reminders_sent += 1
        REMINDERS_SENT.labels(type="reminder").inc()

    def inc_broadcast(self) -> None:
        self.reminders_sent += 1
        BROADCAST_SENT.labels(status="sent").inc()

    def inc_errors(self) -> None:
        self.errors += 1
        ERROR_HANDLER_ERRORS.labels(error_type="domain").inc()

    def uptime_seconds(self) -> float:
        return time.time() - self._start


async def health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def metrics(request: web.Request) -> web.Response:
    return web.Response(body=generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


def create_metrics_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/metrics", metrics)
    return app


async def start_metrics_server(port: int) -> web.AppRunner:
    runner = web.AppRunner(create_metrics_app())
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Metrics server started on port %s", port)
    return runner


def start_metrics(port: int = 9090) -> None:
    # Legacy sync version for compatibility
    import threading
    def run():
        import asyncio
        asyncio.run(start_metrics_server(port))
    threading.Thread(target=run, daemon=True).start()
