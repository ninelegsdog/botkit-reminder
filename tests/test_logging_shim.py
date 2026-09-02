"""Cover src/core/logging.py shim."""
from __future__ import annotations

import asyncio
import io
import json
import logging

from src.core.logging import (
    LoggingMiddleware,
    get_conversation_id,
    set_bot_name,
    set_conversation_id,
    setup_logging,
)


def _clear_root_handlers() -> None:
    root = logging.getLogger()
    root.handlers.clear()


def test_logging_middleware_sets_conversation_id() -> None:
    mw = LoggingMiddleware()

    class FakeChat:
        id = 123

    class FakeEvent:
        chat = FakeChat()

    async def handler(event: object, data: dict[str, object]) -> str:
        return get_conversation_id()

    result = asyncio.run(mw(handler, FakeEvent(), {}))
    assert result == "123"
    set_conversation_id("-")


def test_logging_middleware_falls_back_to_user() -> None:
    mw = LoggingMiddleware()

    class FakeUser:
        id = 456

    class FakeEvent:
        from_user = FakeUser()

    async def handler(event: object, data: dict[str, object]) -> str:
        return get_conversation_id()

    result = asyncio.run(mw(handler, FakeEvent(), {}))
    assert result == "456"
    set_conversation_id("-")


def test_logging_middleware_falls_back_to_message() -> None:
    mw = LoggingMiddleware()

    class FakeChat:
        id = 789

    class FakeMessage:
        chat = FakeChat()

    class FakeEvent:
        message = FakeMessage()

    async def handler(event: object, data: dict[str, object]) -> str:
        return get_conversation_id()

    result = asyncio.run(mw(handler, FakeEvent(), {}))
    assert result == "789"
    set_conversation_id("-")


def test_setup_logging_json_emits_structured_record() -> None:
    stream = io.StringIO()
    set_bot_name("reminder")
    setup_logging(level="INFO", json=True, bot_name="reminder", stream=stream)
    try:
        logging.getLogger().info("hello %s", "world")
        line = stream.getvalue().strip().splitlines()[-1]
        record = json.loads(line)
        assert record["message"] == "hello world"
        assert record["conversation_id"] == "-"
        assert record["bot"] == "reminder"
        assert "levelname" in record
    finally:
        _clear_root_handlers()


def test_setup_logging_plain_outputs_text() -> None:
    stream = io.StringIO()
    setup_logging(level="INFO", json=False, bot_name="reminder", stream=stream)
    try:
        logging.getLogger().info("plain message")
        line = stream.getvalue().strip()
        assert "plain message" in line
        assert not line.lstrip().startswith("{")
    finally:
        _clear_root_handlers()
