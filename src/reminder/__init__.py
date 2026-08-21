from __future__ import annotations

from typing import Any


def register_routers(state: Any) -> None:
    from src.admin.handlers import create_router as admin_router
    from src.reminder.handlers import create_router as reminder_router
    state.dp.include_router(reminder_router())
    state.dp.include_router(admin_router())
