from __future__ import annotations

import pytest

from src.core.auth import admin_gate, is_admin, verify_password
from src.core.database import get_session
from src.core.ui import escape


def test_escape_html() -> None:
    assert escape("<script>") == "&lt;script&gt;"
    assert escape("safe") == "safe"


def test_verify_password_default() -> None:
    assert verify_password("admin") is True
    assert verify_password("wrong") is False


def test_admin_gate() -> None:
    admin_gate.login(1)
    assert admin_gate.is_authorized(1) is True
    admin_gate.logout(1)
    assert admin_gate.is_authorized(1) is False


def test_is_admin() -> None:
    assert is_admin(123) is True
    assert is_admin(999999999) is False


@pytest.mark.asyncio
async def test_db_session() -> None:
    async with get_session() as session:
        assert session is not None
