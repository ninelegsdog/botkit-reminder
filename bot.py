from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from src.core.bot_factory import state
from src.core.config import settings
from src.core.errors import register_error_handler
from src.core.logging import configure_logging
from src.core.metrics import start_metrics
from src.core.webhook import app as webhook_app
from src.reminder import register_routers

configure_logging()
logger = logging.getLogger(__name__)


def _setup_dp() -> None:
    from src.core.throttling import ThrottlingMiddleware
    state.dp.message.middleware(ThrottlingMiddleware())
    register_error_handler(state.dp)
    register_routers(state)


async def _run_polling() -> None:
    _setup_dp()
    await state.bot.delete_webhook(drop_pending_updates=True)
    logger.info("Starting polling")
    await state.dp.start_polling(state.bot)


async def _run_webhook() -> None:
    _setup_dp()
    webhook_path = f"/webhook/{settings.telegram_bot_token}"
    await state.bot.set_webhook(
        f"https://botkit-reminder.onrender.com{webhook_path}",
        secret_token=settings.telegram_webhook_secret,
    )
    logger.info("Webhook set to %s", webhook_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _run_webhook()
    start_metrics(9090)
    yield


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.mount("/", webhook_app)
    return app


async def main() -> None:
    import sys
    if "--webhook" in sys.argv:
        await _run_webhook()
        stop_event = asyncio.Event()
        with suppress(asyncio.CancelledError):
            await stop_event.wait()
    else:
        await _run_polling()


if __name__ == "__main__":
    asyncio.run(main())
