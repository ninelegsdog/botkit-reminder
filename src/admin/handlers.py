from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.admin.service import AdminService
from src.core.auth import admin_only
from src.core.navigation import reply_menu
from src.core.ui import escape

logger = logging.getLogger(__name__)


def create_router() -> Router:
    router = Router()

    @router.message(Command("admin"))
    async def admin_entry(message: Message, state: Any) -> None:
        await message.answer("Введите пароль:")
        await state.set_state("admin:password")

    @router.message(F.state == "admin:password")
    async def admin_password(message: Message, state: Any) -> None:
        from src.core.auth import admin_gate, verify_password
        if not message.from_user or not message.text:
            return
        if verify_password(message.text):
            admin_gate.login(message.from_user.id)
            await state.clear()
            await message.answer(
                "✅ Админ-доступ открыт",
                reply_markup=reply_menu(
                    "📊 Статистика",
                    "📣 Рассылка",
                    "👥 Подписчики",
                ),
            )
        else:
            await message.answer("❌ Неверный пароль")

    @admin_only
    @router.message(F.text == "📊 Статистика")
    async def admin_stats(message: Message) -> None:
        from src.core.database import get_session
        async with get_session() as session:
            service = AdminService(session)
            stats = await service.stats()
        await message.answer(f"Подписчиков: {stats['subscribers']}\nНапоминаний: {stats['reminders']}")

    @admin_only
    @router.message(F.text == "👥 Подписчики")
    async def admin_subscribers(message: Message) -> None:
        from src.core.database import get_session
        async with get_session() as session:
            service = AdminService(session)
            subs = await service.subscribers()
        lines = [f"{s.user_id} @{escape(s.username or '-')} {escape(s.name or '')}" for s in subs[:50]]
        await message.answer("\n".join(lines) or "Нет подписчиков")

    return router
