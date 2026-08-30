from __future__ import annotations

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI

from src.core.bot_factory import state
from src.core.cache import cache
from src.core.commands import set_commands
from src.core.config import settings
from src.core.errors import register_error_handler
from src.core.logging import configure_logging
from src.core.metrics import start_metrics
from src.core.sentry import init_sentry
from src.core.webhook import app as webhook_app
from src.core.webhook import set_webhook_dispatcher
from src.reminder import register_routers
from src.reminder.scheduler import Scheduler

configure_logging()
init_sentry()
logger = logging.getLogger(__name__)


def _setup_dp() -> None:
    from src.core.throttling import ThrottlingMiddleware
    state.dp.message.middleware(ThrottlingMiddleware(redis_url=settings.redis_url))
    register_error_handler(state.dp)
    register_routers(state)
    set_webhook_dispatcher(state.dp)


async def _run_polling() -> None:
    _setup_dp()
    await state.bot.delete_webhook(drop_pending_updates=True)
    await set_commands(state.bot)
    logger.info("Starting polling")
    await state.dp.start_polling(state.bot)


async def _run_webhook() -> None:
    _setup_dp()
    await set_commands(state.bot)
    webhook_base = settings.webhook_url.rstrip("/") if settings.webhook_url else "https://botkit-reminder.onrender.com"
    webhook_path = f"/webhook/{settings.telegram_bot_token.split(':')[0]}"
    full_webhook_url = f"{webhook_base}{webhook_path}"
    await state.bot.set_webhook(
        full_webhook_url,
        secret_token=settings.telegram_webhook_secret,
    )
    logger.info("Webhook set to %s", full_webhook_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.core.database import async_session
    await cache.init()
    scheduler = Scheduler(async_session, state.bot.send_message)
    scheduler.start()
    if settings.webhook_url:
        await _run_webhook()
    else:
        logger.info("WEBHOOK_URL not set, running in polling mode (FastAPI only for health/metrics)")
    start_metrics(settings.metrics_port)
    try:
        yield
    finally:
        scheduler.stop()
        await state.bot.session.close()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.mount("/", webhook_app)
    return app


async def main() -> None:
    stop_event = asyncio.Event()
    
    def handle_signal(sig: int, frame: Any) -> None:
        logger.info("Received signal %s, shutting down...", sig)
        stop_event.set()
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    
    if "--webhook" in sys.argv or settings.webhook_url:
        await _run_webhook()
        with suppress(asyncio.CancelledError):
            await stop_event.wait()
    else:
        _setup_dp()
        await state.bot.delete_webhook(drop_pending_updates=True)
        await set_commands(state.bot)
        from src.core.database import Base, async_session, engine

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        start_metrics(settings.metrics_port)
        scheduler = Scheduler(async_session, state.bot.send_message)
        scheduler.start()
        logger.info("Starting polling")
        try:
            await state.dp.start_polling(state.bot)
        finally:
            scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
