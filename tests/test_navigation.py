from __future__ import annotations

from src.core.navigation import compose_message, inline_buttons, nav_header, reply_menu


def test_compose_message() -> None:
    result = compose_message("Title", "Body")
    assert "<b>Title</b>" in result
    assert "Body" in result


def test_nav_header() -> None:
    assert nav_header("A", "B", "C") == "A › B › C"
    assert nav_header("A") == "A"


def test_reply_menu() -> None:
    kb = reply_menu("A", "B")
    assert kb.keyboard is not None


def test_inline_buttons() -> None:
    kb = inline_buttons([[("A", "a")], [("B", "b")]])
    assert kb.inline_keyboard is not None
