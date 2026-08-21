from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Generator
from typing import Any

import pytest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:ABC")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "secret")
os.environ.setdefault("TELEGRAM_ADMIN_IDS", "123")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918")

from src.core.bot_factory import AppState  # noqa: E402


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def tmp_db() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        yield db


@pytest.fixture
def app_state() -> Any:
    return AppState()
