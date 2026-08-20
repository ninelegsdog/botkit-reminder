from src.reminder.handlers import create_router as reminder_router
from src.admin.handlers import create_router as admin_router


def register_routers(state) -> None:
    state.dp.include_router(reminder_router())
    state.dp.include_router(admin_router())
