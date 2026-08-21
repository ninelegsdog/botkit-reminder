from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.auth import admin_only
from src.core.database import get_session
from src.core.navigation import compose_message, nav_header, reply_menu
from src.core.ui import escape
from src.reminder.models import Reminder, ReminderType
from src.reminder.service import BroadcastService, ReminderService, SubscriptionService

logger = logging.getLogger(__name__)


def _delete_button(reminder_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="🗑 Удалить", callback_data=f"rem:confirm:delete:{reminder_id}"))
    kb.add(InlineKeyboardButton(text="❌ Отмена", callback_data="rem:cancel"))
    kb.adjust(2)
    return kb.as_markup()


def create_router() -> Router:
    router = Router()

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        text = compose_message(
            nav_header("ReminderBot"),
            "Подпишитесь на напоминания и рассылки. Или начните с кнопки ниже.",
        )
        await message.answer(
            text,
            reply_markup=reply_menu(
                "⏰ Мои напоминания",
                "📣 Рассылки",
                "➕ Добавить",
                "🔔 Подписаться",
                "🔕 Отписаться",
            ),
        )

    @router.message(F.text == "🔔 Подписаться")
    async def subscribe(message: Message) -> None:
        if not message.from_user:
            return
        async with get_session() as session:
            service = SubscriptionService(session)
            await service.subscribe(message.from_user.id, message.from_user.username, message.from_user.full_name)
        await message.answer(
            "✅ Вы подписаны на рассылки",
            reply_markup=reply_menu(
                "⏰ Мои напоминания",
                "📣 Рассылки",
                "➕ Добавить",
                "🔕 Отписаться",
            ),
        )

    @router.message(F.text == "🔕 Отписаться")
    async def unsubscribe(message: Message) -> None:
        if not message.from_user:
            return
        async with get_session() as session:
            service = SubscriptionService(session)
            await service.unsubscribe(message.from_user.id)
        await message.answer(
            "✅ Вы отписались от рассылок",
            reply_markup=reply_menu(
                "⏰ Мои напоминания",
                "📣 Рассылки",
                "➕ Добавить",
                "🔔 Подписаться",
            ),
        )

    @router.message(F.text == "➕ Добавить")
    async def add_reminder_start(message: Message, state: FSMContext) -> None:
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="🔸 Одноразовое", callback_data="rem:type:once"))
        kb.add(InlineKeyboardButton(text="🔁 Повторяющееся", callback_data="rem:type:recurring"))
        kb.adjust(2)
        await message.answer("Выберите тип напоминания:", reply_markup=kb.as_markup())

    @router.callback_query(F.data == "rem:type:once")
    async def once_type(callback: CallbackQuery, state: FSMContext) -> None:
        await state.update_data(type=ReminderType.once.value)
        if callback.message:
            await callback.message.edit_text("Введите дату в формате ДД.ММ.ГГГГ")  # type: ignore[union-attr]
        await state.set_state("reminder:date")

    @router.callback_query(F.data == "rem:type:recurring")
    async def recurring_type(callback: CallbackQuery, state: FSMContext) -> None:
        await state.update_data(type=ReminderType.recurring.value)
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        kb = InlineKeyboardBuilder()
        for i, d in enumerate(days):
            kb.add(InlineKeyboardButton(text=d, callback_data=f"rem:day:{i}"))
        kb.adjust(4)
        if callback.message:
            await callback.message.edit_text("Выберите день недели:", reply_markup=kb.as_markup())  # type: ignore[union-attr]

    @router.callback_query(F.data.startswith("rem:day:"))
    async def day_selected(callback: CallbackQuery, state: FSMContext) -> None:
        day = callback.data.split(":")[-1]  # type: ignore[union-attr]
        await state.update_data(cron_day=day)
        if callback.message:
            await callback.message.edit_text("Введите время ЧЧ:ММ")  # type: ignore[union-attr]
        await state.set_state("reminder:time")

    @router.message(F.state == "reminder:date")
    async def date_entered(message: Message, state: FSMContext) -> None:
        if not message.text:
            return
        try:
            fire_at = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        except ValueError:
            await message.answer("Неверный формат. Введите ДД.ММ.ГГГГ")
            return
        await state.update_data(fire_at=fire_at.date().isoformat())
        await message.answer("Введите время ЧЧ:ММ")
        await state.set_state("reminder:time")

    @router.message(F.state == "reminder:time")
    async def time_entered(message: Message, state: FSMContext) -> None:
        if not message.text:
            return
        try:
            h, m = map(int, message.text.strip().split(":"))
        except Exception:
            await message.answer("Неверный формат. Введите ЧЧ:ММ")
            return
        data = await state.get_data()
        fire_at_str = data.get("fire_at")
        if fire_at_str:
            fire_at = datetime.fromisoformat(fire_at_str).replace(hour=h, minute=m)
        else:
            await message.answer("Сначала выберите тип и параметры")
            await state.clear()
            return
        text = data.get("text") or message.text
        async with get_session() as session:
            service = ReminderService(session, None)
            reminder = await service.create_reminder(
                creator_id=message.from_user.id if message.from_user else 0,
                type=ReminderType(data["type"]),
                text=text or "Напоминание",
                fire_at=fire_at,
                cron_day=data.get("cron_day"),
            )
        await state.clear()
        await message.answer(
            f"✅ Напоминание создано! ID: {reminder.id}",
            reply_markup=reply_menu(
                "⏰ Мои напоминания",
                "📣 Рассылки",
                "➕ Добавить",
            ),
        )

    @router.message(F.text == "⏰ Мои напоминания")
    async def my_reminders(message: Message) -> None:
        if not message.from_user:
            return
        async with get_session() as session:
            from sqlalchemy import select
            stmt = select(Reminder).where(Reminder.creator_id == message.from_user.id).order_by(Reminder.id.desc())
            result = await session.execute(stmt)
            reminders = result.scalars().all()
        if not reminders:
            await message.answer(
                "Нет напоминаний",
                reply_markup=reply_menu("➕ Добавить", "📣 Рассылки"),
            )
            return
        lines = []
        for r in reminders:
            when = r.fire_at.strftime("%d.%m.%Y %H:%M") if r.fire_at else r.cron_day or "?"
            lines.append(f"#{r.id} {r.type.value} {when} — {escape(r.text)}")
        await message.answer(
            "\n".join(lines),
            reply_markup=reply_menu(
                "⏰ Мои напоминания",
                "📣 Рассылки",
                "➕ Добавить",
            ),
        )

    @router.callback_query(F.data.startswith("rem:delete:"))
    async def delete_reminder_prompt(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        reminder_id = int(callback.data.split(":")[-1])
        if callback.message:
            await callback.message.edit_text("❓ Удалить это напоминание?", reply_markup=_delete_button(reminder_id))  # type: ignore[union-attr]

    @router.callback_query(F.data.startswith("rem:confirm:delete:"))
    async def delete_reminder_confirm(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        reminder_id = int(callback.data.split(":")[-1])
        async with get_session() as session:
            from sqlalchemy import delete as sqla_delete
            await session.execute(sqla_delete(Reminder).where(Reminder.id == reminder_id))
            await session.commit()
        if callback.message:
            await callback.message.edit_text("✅ Напоминание удалено")  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data == "rem:cancel")
    async def delete_cancel(callback: CallbackQuery) -> None:
        if callback.message:
            await callback.message.edit_text("❌ Отменено")  # type: ignore[union-attr]
        await callback.answer()

    @router.message(F.text == "📣 Рассылки")
    async def broadcasts(message: Message, state: FSMContext) -> None:
        if not message.from_user:
            return
        async with get_session() as session:
            service = SubscriptionService(session)
            sub = await service.get_subscriber(message.from_user.id)
            if not sub or not sub.is_active:
                await message.answer(
                    "🔕 Вы не подписаны на рассылки. Подпишитесь сначала.",
                    reply_markup=reply_menu("🔔 Подписаться", "⏰ Мои напоминания"),
                )
                return
        await message.answer("Введите текст рассылки:")
        await state.set_state("broadcast:text")

    @router.message(F.state == "broadcast:text")
    async def broadcast_text(message: Message, state: FSMContext) -> None:
        if not message.text:
            return
        async with get_session() as session:
            service = BroadcastService(session, None)
            broadcast = await service.create_broadcast(message.text, segment="active")
            await service.send_broadcast(broadcast.id)
        await state.clear()
        await message.answer(
            f"✅ Рассылка отправлена! ID: {broadcast.id}",
            reply_markup=reply_menu(
                "⏰ Мои напоминания",
                "📣 Рассылки",
                "➕ Добавить",
            ),
        )

    @router.message(Command("admin"))
    async def admin_entry(message: Message, state: FSMContext) -> None:
        await message.answer("Введите пароль:")
        await state.set_state("admin:password")

    @router.message(F.state == "admin:password")
    async def admin_password(message: Message, state: FSMContext) -> None:
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
        from src.admin.service import AdminService
        async with get_session() as session:
            service = AdminService(session)
            stats = await service.stats()
        await message.answer(f"Подписчиков: {stats['subscribers']}\nНапоминаний: {stats['reminders']}")

    @admin_only
    @router.message(F.text == "👥 Подписчики")
    async def admin_subscribers(message: Message) -> None:
        from src.admin.service import AdminService
        async with get_session() as session:
            service = AdminService(session)
            subs = await service.subscribers()
        lines = [f"{s.user_id} @{escape(s.username or '-')} {escape(s.name or '')}" for s in subs[:50]]
        await message.answer("\n".join(lines) or "Нет подписчиков")

    return router
