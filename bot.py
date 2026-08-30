from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from aiogram.types import BufferedInputFile
from aiohttp import web

from src.core.bot_factory import state
from src.core.cache import cache
from src.core.commands import set_commands
from src.core.config import settings
from src.core.errors import register_error_handler
from src.core.logging import configure_logging
from src.core.metrics import health, metrics, start_metrics_server
from src.core.sentry import init_sentry
from src.core.tgwebhook import build_webhook_app
from src.core.throttling import ThrottlingMiddleware
from src.reminder import register_routers
from src.reminder.scheduler import Scheduler


def _load_cert(path: str) -> BufferedInputFile | None:
    cert_path = Path(path)
    if not cert_path.is_file():
        return None
    return BufferedInputFile(cert_path.read_bytes(), filename="webhook_public.pem")


def _setup_dp() -> None:
    state.dp.message.middleware(ThrottlingMiddleware(redis_url=settings.redis_url))
    register_error_handler(state.dp)
    register_routers(state)


async def _run_webhook(shutdown_event: asyncio.Event) -> None:
    _setup_dp()
    await set_commands(state.bot)
    await cache.init()

    scheduler = Scheduler(state.db.async_session, state.bot.send_message)
    scheduler.start()

    app = build_webhook_app(state.dp, state.bot, settings.telegram_webhook_secret)
    app["state"] = state
    app.router.add_get("/health", health)
    app.router.add_get("/metrics", metrics)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.metrics_port)
    await site.start()
    logging.info("Webhook HTTP server listening on :%s", settings.metrics_port)

    await state.bot.delete_webhook(drop_pending_updates=True)
    cert = await asyncio.to_thread(_load_cert, settings.webhook_cert_path)
    if cert is None:
        logging.warning("WEBHOOK_CERT_PATH not found: %s", settings.webhook_cert_path)
    else:
        logging.info("Using webhook certificate")
    await state.bot.set_webhook(
        url=settings.webhook_url,
        secret_token=settings.telegram_webhook_secret or None,
        certificate=cert,
    )
    logging.info("Telegram webhook registered: %s", settings.webhook_url)
    try:
        await shutdown_event.wait()
    finally:
        scheduler.stop()
        await state.bot.delete_webhook()
        await runner.cleanup()
        await state.bot.session.close()


async def _run_polling(shutdown_event: asyncio.Event) -> None:
    _setup_dp()
    await state.bot.delete_webhook(drop_pending_updates=True)
    await set_commands(state.bot)
    await cache.init()

    from src.core.database import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    runner = await start_metrics_server(settings.metrics_port)
    scheduler = Scheduler(state.db.async_session, state.bot.send_message)
    scheduler.start()
    logging.info("Starting polling")
    try:
        await asyncio.wait([
            asyncio.create_task(state.dp.start_polling(state.bot)),
            asyncio.create_task(shutdown_event.wait()),
        ])
    finally:
        scheduler.stop()
        await state.dp.stop_polling()
        await state.bot.session.close()
        await runner.cleanup()


async def main() -> None:
    configure_logging()
    init_sentry(settings.sentry_dsn)
    state.config.validate()
    logging.basicConfig(level=settings.log_level)

    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    if settings.webhook_url:
        await _run_webhook(shutdown_event)
    else:
        await _run_polling(shutdown_event)


if __name__ == "__main__":
    asyncio.run(main())
