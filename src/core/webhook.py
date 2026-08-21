from __future__ import annotations

import hmac
from typing import Any

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request, Response

from src.core.bot_factory import state
from src.core.config import settings
from src.core.metrics import WEBHOOK_REQUESTS

app = FastAPI()
_webhook_dispatcher: Any = None


def set_webhook_dispatcher(dispatcher: Any) -> None:
    global _webhook_dispatcher
    _webhook_dispatcher = dispatcher


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/metrics")
async def metrics() -> Response:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request) -> dict[str, str | bool]:
    WEBHOOK_REQUESTS.labels(status="received").inc()
    if settings.telegram_webhook_secret and settings.telegram_webhook_secret != "change-me":
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
