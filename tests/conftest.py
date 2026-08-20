from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
import pytest_asyncio
from aiogram.fsm.storage.memory import MemoryStorage

from src.core.bot_factory import AppState
from src.core.config import Settings, settings


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
