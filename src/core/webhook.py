from __future__ import annotations

import hmac
from typing import Any

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from src.core.bot_factory import state
from src.core.config import settings
from src.core.metrics import WEBHOOK_REQUESTS

app = FastAPI(
    title="BotKit Reminder API",
    description="Telegram bot webhook API for reminders and newsletters",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
_webhook_dispatcher: Any = None


def set_webhook_dispatcher(dispatcher: Any) -> None:
    global _webhook_dispatcher
    _webhook_dispatcher = dispatcher


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "TelegramWebhookSecret": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Telegram-Bot-Api-Secret-Token",
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method["security"] = [{"TelegramWebhookSecret": []}]
    app.openapi_schema = openapi_schema
    return openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/health", response_model=None)
async def health() -> dict[str, str] | Response:
    try:
        from src.core.database import async_session

        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return Response(status_code=500, content="db unavailable")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    try:
        from src.core.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not ready"}


@app.get("/metrics")
async def metrics() -> Response:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request) -> dict[str, str | bool]:
    WEBHOOK_REQUESTS.labels(status="received").inc()
    if not settings.telegram_webhook_secret or settings.telegram_webhook_secret == "change-me":
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret or not hmac.compare_digest(secret, settings.telegram_webhook_secret):
        WEBHOOK_REQUESTS.labels(status="forbidden").inc()
        raise HTTPException(status_code=403, detail="Forbidden")
    if bot_token != settings.telegram_bot_token.split(":")[0]:
        WEBHOOK_REQUESTS.labels(status="forbidden").inc()
        raise HTTPException(status_code=403, detail="Forbidden")
    WEBHOOK_REQUESTS.labels(status="ok").inc()
    if _webhook_dispatcher is None:
        raise HTTPException(status_code=500, detail="Webhook dispatcher not initialized")
    data = await request.json()
    update = Update.model_validate(data)
    await _webhook_dispatcher.feed_webhook_update(state.bot, update)
    return {"ok": True}