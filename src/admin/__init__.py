from src.admin.handlers import create_router as admin_router


def register_routers(state) -> None:
    state.dp.include_router(admin_router())
