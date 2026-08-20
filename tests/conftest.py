from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:ABC")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "secret")
os.environ.setdefault("TELEGRAM_ADMIN_IDS", "123")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "change-me")

from src.core.bot_factory import AppState


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_db():
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        yield db


@pytest.fixture
def app_state():
    return AppState()
