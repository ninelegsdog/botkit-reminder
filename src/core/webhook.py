from __future__ import annotations

import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException, Response

from src.core.config import settings

app = FastAPI()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> Response:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request) -> dict[str, str]:
    if settings.telegram_webhook_secret and settings.telegram_webhook_secret != "change-me":
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not secret or not hmac.compare_digest(secret, settings.telegram_webhook_secret):
            raise HTTPException(status_code=403, detail="Forbidden")
    if bot_token != settings.telegram_bot_token.split(":")[0]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"ok": True}
