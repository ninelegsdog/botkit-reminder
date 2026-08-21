from __future__ import annotations

import hmac

from fastapi import FastAPI, HTTPException, Request, Response

from src.core.config import settings
from src.core.metrics import WEBHOOK_REQUESTS

app = FastAPI()


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
    return {"ok": True}
