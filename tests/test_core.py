from __future__ import annotations

import pytest

from src.core.config import Config
from src.core.ui import broadcast_card, escape, reminder_card


@pytest.mark.asyncio
async def test_config_from_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test_token")
    config = Config.from_env()
    assert config.bot_token == "test_token"


def test_escape():
    assert escape("<script>") == "&lt;script&gt;"
    assert escape("hello") == "hello"
    assert escape(None) == ""


def test_reminder_card():
    card = reminder_card({
        "id": 1,
        "type": "once",
        "text": "Test <script>",
        "is_active": 1,
    })
    assert "<script>" not in card
    assert "Напоминание #1" in card


def test_broadcast_card():
    card = broadcast_card({
        "id": 1,
        "text": "Hello <b>world</b>",
        "delivered": 10,
        "total": 15,
    })
    assert "<b>" not in card
    assert "10/15" in card
