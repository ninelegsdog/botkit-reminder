from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
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


_PAYLOADS_DIR = Path(__file__).parent / "fixtures" / "payloads"


@pytest.fixture
def load_payload() -> Any:
    """Load a JSON Telegram-update fixture from tests/fixtures/payloads/."""

    def _load(name: str) -> dict[str, Any]:
        return json.loads((_PAYLOADS_DIR / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    return _load


def pytest_collection_modifyitems(config: Any, items: Any) -> None:
    """Tag offline tests as no_req; skip real Telegram (req) tests unless RUN_TELEGRAM_E2E=1."""
    for item in items:
        path = getattr(item, "path", None)
        fname = Path(path).name if path else ""
        is_req_file = fname == "test_e2e.py"
        if "req" in item.keywords or is_req_file:
            if os.getenv("RUN_TELEGRAM_E2E") != "1":
                item.add_marker(
                    pytest.mark.skip(reason="set RUN_TELEGRAM_E2E=1 to run real Telegram tests")
                )
        elif "no_req" not in item.keywords:
            item.add_marker(pytest.mark.no_req)
