"""The admin password check must actually enforce an attempt limit.

`AdminGate` in this bot tracked who was authorised but recorded nothing about failures,
so `/admin` accepted unlimited password guesses. The class looked like protection and
provided none. These tests pin the behaviour that is now reachable from Telegram.
"""

from __future__ import annotations

import time

from src.core.auth import AdminGate

PASSWORD = "correct horse battery staple"


def test_failures_are_recorded_and_throttled() -> None:
    gate = AdminGate()
    uid = 42
    assert gate.is_throttled(uid) is False
    for _ in range(5):
        gate.record_failure(uid)
    assert gate.is_throttled(uid) is True


def test_successful_login_clears_attempts() -> None:
    gate = AdminGate()
    uid = 7
    for _ in range(3):
        gate.record_failure(uid)
    gate.login(uid)
    assert gate.is_authorized(uid) is True
    assert gate.is_throttled(uid) is False


def test_throttle_window_expires() -> None:
    gate = AdminGate()
    gate._WINDOW = 0.2  # shrink instead of sleeping for 5 minutes
    uid = 9
    for _ in range(5):
        gate.record_failure(uid)
    assert gate.is_throttled(uid) is True
    time.sleep(0.25)
    assert gate.is_throttled(uid) is False


def test_logout_removes_authorization() -> None:
    gate = AdminGate()
    gate.login(3)
    assert gate.is_authorized(3) is True
    gate.logout(3)
    assert gate.is_authorized(3) is False


def test_attempts_are_tracked_per_user() -> None:
    """One user's failures must not lock out everyone else."""
    gate = AdminGate()
    for _ in range(5):
        gate.record_failure(1)
    assert gate.is_throttled(1) is True
    assert gate.is_throttled(2) is False
