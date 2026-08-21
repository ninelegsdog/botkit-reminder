from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.bot_factory import AppState
from src.core.fsm import AdminAuth
from src.core.nav import admin_menu, client_menu
from src.reminder import service


def create_admin_router(state: AppState) -> Router:
    router = Router()
    db = state.db

    def is_admin(user_id: int) -> bool:
        return user_id == 123456789  # TODO: real admin check

    @router.message(Command("admin"))
    async def cmd_admin(message: Message, state_fsm: FSMContext) -> None:
        await state_fsm.set_state(AdminAuth.waiting_password)
        await message.answer("🔑 Введите пароль:")

    @router.message(AdminAuth.waiting_password)
    async def check_password(message: Message, state_fsm: FSMContext) -> None:
        if message.text == state.config.admin_password:
            await state_fsm.clear()
            await message.answer("✅ Добро пожаловать!", reply_markup=admin_menu())
        else:
            await state_fsm.clear()
            await message.answer("❌ Неверный пароль.", reply_markup=client_menu())

    @router.message(F.text == "👥 Подписчики")
    async def list_subscribers(message: Message) -> None:
        if not is_admin(message.from_user.id):  # type: ignore[union-attr]
            return
        subscribers = await service.get_active_subscribers(db)
        if not subscribers:
            await message.answer("Нет подписчиков.")
            return
        text = "👥 Подписчики:\n" + "\n".join(
            f"• {s['user_id']} (@{s.get('username', 'N/A')})" for s in subscribers
        )
        await message.answer(text)

    @router.message(F.text == "📊 Статистика")
    async def admin_stats(message: Message) -> None:
        if not is_admin(message.from_user.id):  # type: ignore[union-attr]
            return
        subscribers = await service.get_active_subscribers(db)
        await message.answer(
            f"📊 Статистика:\n"
            f"  Подписчиков: {len(subscribers)}\n"
        )

    @router.message(F.text == "📣 Рассылка")
    async def start_broadcast(message: Message) -> None:
        if not is_admin(message.from_user.id):  # type: ignore[union-attr]
            return
        await message.answer("📝 Введите текст рассылки:")

    return router
