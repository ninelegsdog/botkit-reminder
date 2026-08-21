from __future__ import annotations

from src.core.ui import escape, truncate


def test_escape() -> None:
    assert escape("<script>") == "&lt;script&gt;"
    assert escape("safe") == "safe"


def test_truncate() -> None:
    assert truncate("hello") == "hello"
    long = "a" * 100
    assert len(truncate(long, 10)) == 10
    assert truncate(long, 10).endswith("...")
