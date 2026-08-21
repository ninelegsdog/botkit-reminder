from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from pydantic_settings import SettingsConfigDict

from src.core.config import Settings
from src.core.webhook import app

client = TestClient(app)


class _TestSettings(Settings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")


def _make_settings(**kwargs: Any) -> Settings:
    return _TestSettings(
        telegram_bot_token="123:ABC",
        telegram_admin_ids="123",
        admin_password_hash="change-me",
        **kwargs,
    )


def test_webhook_rejects_wrong_bot_token(monkeypatch: Any) -> None:
    settings = _make_settings()
    monkeypatch.setattr("src.core.webhook.settings", settings)
    response = client.post("/webhook/wrong")
    assert response.status_code == 403


def test_webhook_accepts_correct_bot_token_without_secret(monkeypatch: Any) -> None:
    settings = _make_settings(telegram_webhook_secret="change-me")
    monkeypatch.setattr("src.core.webhook.settings", settings)
    response = client.post("/webhook/123")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_rejects_missing_secret_when_configured(monkeypatch: Any) -> None:
    settings = _make_settings(telegram_webhook_secret="mysecret")
    monkeypatch.setattr("src.core.webhook.settings", settings)
    response = client.post("/webhook/123")
    assert response.status_code == 403


def test_webhook_accepts_valid_secret(monkeypatch: Any) -> None:
    settings = _make_settings(telegram_webhook_secret="mysecret")
    monkeypatch.setattr("src.core.webhook.settings", settings)
    response = client.post("/webhook/123", headers={"X-Telegram-Bot-Api-Secret-Token": "mysecret"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_rejects_invalid_secret(monkeypatch: Any) -> None:
    settings = _make_settings(telegram_webhook_secret="mysecret")
    monkeypatch.setattr("src.core.webhook.settings", settings)
    response = client.post("/webhook/123", headers={"X-Telegram-Bot-Api-Secret-Token": "wrongsecret"})
    assert response.status_code == 403
