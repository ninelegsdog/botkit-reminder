from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.core.bot_factory import create_bot
from src.core.webhook import app


@pytest.fixture
def app_state() -> Any:
    state = create_bot()
    state.dp = Dispatcher(storage=MemoryStorage())
    return state


@pytest.fixture
def mock_uow() -> Any:
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.session = session
    return uow


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_secret() -> None:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(
        "/webhook/123",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        json={"update_id": 1},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_token() -> None:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post(
        "/webhook/wrong",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
        json={"update_id": 1},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_accepts_valid_request() -> None:
    from fastapi.testclient import TestClient

    from src.core.config import settings
    client = TestClient(app)
    token_prefix = settings.telegram_bot_token.split(":")[0]
    payload = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 1234567890,
            "chat": {"id": 1, "type": "private"},
            "from": {"id": 1, "is_bot": False, "first_name": "Test"},
            "text": "/start",
        },
    }
    response = client.post(
        f"/webhook/{token_prefix}",
        headers={"X-Telegram-Bot-Api-Secret-Token": settings.telegram_webhook_secret},
        json=payload,
    )
    assert response.status_code == 500  # dispatcher not set


@pytest.mark.asyncio
async def test_health_endpoints() -> None:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert client.get("/metrics").status_code == 200
