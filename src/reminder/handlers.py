from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.bot_factory import AppState
from src.core.fsm import ReminderOnce, ReminderRecurring
from src.core.nav import client_menu
from src.core.ui import escape, reminder_card
from src.reminder import service


def create_reminder_router(state: AppState) -> Router:
    router = Router()
    db = state.db

    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await service.subscribe(
            db,
            message.from_user.id,  # type: ignore[union-attr]
            getattr(message.from_user, "username", None),
            getattr(message.from_user, "first_name", None),
        )
        await message.answer(
            "⏰ Подпишитесь на напоминания!",
            reply_markup=client_menu(),
        )

    @router.message(F.text == "➕ Добавить")
    async def start_add(message: Message) -> None:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔸 Одноразовое", callback_data="rem_type:once")],
                [InlineKeyboardButton(text="🔁 Повторяющееся", callback_data="rem_type:recurring")],
            ]
        )
        await message.answer("Выберите тип:", reply_markup=kb)

    @router.callback_query(F.data == "rem_type:once")
    async def choose_once(callback: CallbackQuery, state_fsm: FSMContext) -> None:
        await state_fsm.set_state(ReminderOnce.entering_date)
        await callback.message.edit_text("📅 Дата (ДД.ММ.ГГГГ):")  # type: ignore[union-attr]
        await callback.answer()

    @router.message(ReminderOnce.entering_date)
    async def enter_date(message: Message, state_fsm: FSMContext) -> None:
        await state_fsm.update_data(date=message.text or "")
        await state_fsm.set_state(ReminderOnce.entering_time)
        await message.answer("⏰ Время (ЧЧ:ММ):")

    @router.message(ReminderOnce.entering_time)
    async def enter_time(message: Message, state_fsm: FSMContext) -> None:
        await state_fsm.update_data(time=message.text or "")
        await state_fsm.set_state(ReminderOnce.entering_text)
        await message.answer("📝 Текст напоминания:")

    @router.message(ReminderOnce.entering_text)
    async def enter_text_once(message: Message, state_fsm: FSMContext) -> None:
        await state_fsm.update_data(text=message.text or "")
        data = await state_fsm.get_data()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Создать", callback_data="rem_once_confirm"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="rem_cancel"),
                ]
            ]
        )
        await state_fsm.set_state(ReminderOnce.confirming)
        await message.answer(
            f"Создать напоминание?\n"
            f"📅 {escape(str(data.get('date', '')))} ⏰ {escape(str(data.get('time', '')))}\n"
            f"📝 {escape(str(data.get('text', '')))}",
            reply_markup=kb,
        )

    @router.callback_query(F.data == "rem_type:recurring")
    async def choose_recurring(callback: CallbackQuery, state_fsm: FSMContext) -> None:
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=d, callback_data=f"rem_day:{i}")]
                for i, d in enumerate(days)
            ]
        )
        await callback.message.edit_text("📅 День недели:", reply_markup=kb)  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data.startswith("rem_day:"))
    async def choose_day(callback: CallbackQuery, state_fsm: FSMContext) -> None:
        if not callback.data:
            return
        day = int(callback.data.split(":")[1])
        await state_fsm.update_data(cron_day=day)
        await state_fsm.set_state(ReminderRecurring.entering_time)
        await callback.message.edit_text("⏰ Время (ЧЧ:ММ):")  # type: ignore[union-attr]
        await callback.answer()

    @router.message(ReminderRecurring.entering_time)
    async def enter_time_recurring(message: Message, state_fsm: FSMContext) -> None:
        await state_fsm.update_data(time=message.text or "")
        await state_fsm.set_state(ReminderRecurring.entering_text)
        await message.answer("📝 Текст напоминания:")

    @router.message(ReminderRecurring.entering_text)
    async def enter_text_recurring(message: Message, state_fsm: FSMContext) -> None:
        await state_fsm.update_data(text=message.text or "")
        data = await state_fsm.get_data()
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = days[int(str(data.get("cron_day", 0)))]
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Создать", callback_data="rem_rec_confirm"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="rem_cancel"),
                ]
            ]
        )
        await state_fsm.set_state(ReminderRecurring.confirming)
        await message.answer(
            f"Создать повторяющееся?\n"
            f"📅 {day_name} ⏰ {escape(str(data.get('time', '')))}\n"
            f"📝 {escape(str(data.get('text', '')))}",
            reply_markup=kb,
        )

    @router.callback_query(F.data == "rem_once_confirm", ReminderOnce.confirming)
    async def confirm_once(callback: CallbackQuery, state_fsm: FSMContext) -> None:
        data = await state_fsm.get_data()
        fire_at = f"{data.get('date', '')} {data.get('time', '')}:00"
        await service.create_reminder(
            db,
            creator_id=callback.from_user.id,
            reminder_type="once",
            fire_at=fire_at,
            text_content=str(data.get("text", "")),
        )
        await state_fsm.clear()
        await callback.message.edit_text("✅ Напоминание создано!")  # type: ignore[union-attr]
        await callback.answer()
        await callback.message.answer("Выберите действие:", reply_markup=client_menu())  # type: ignore[union-attr]

    @router.callback_query(F.data == "rem_rec_confirm", ReminderRecurring.confirming)
    async def confirm_recurring(callback: CallbackQuery, state_fsm: FSMContext) -> None:
        data = await state_fsm.get_data()
        fire_at = "09:00:00"
        await service.create_reminder(
            db,
            creator_id=callback.from_user.id,
            reminder_type="recurring",
            fire_at=fire_at,
            text_content=str(data.get("text", "")),
            cron_day=int(str(data.get("cron_day", 0))),
        )
        await state_fsm.clear()
        await callback.message.edit_text("✅ Повторяющееся напоминание создано!")  # type: ignore[union-attr]
        await callback.answer()
        await callback.message.answer("Выберите действие:", reply_markup=client_menu())  # type: ignore[union-attr]

    @router.callback_query(F.data == "rem_cancel")
    async def cancel_reminder(callback: CallbackQuery, state_fsm: FSMContext) -> None:
        await state_fsm.clear()
        await callback.message.edit_text("Отменено.")  # type: ignore[union-attr]
        await callback.answer()
        await callback.message.answer("Выберите действие:", reply_markup=client_menu())  # type: ignore[union-attr]

    @router.message(F.text == "⏰ Мои напоминания")
    async def my_reminders(message: Message) -> None:
        reminders = await service.get_user_reminders(db, message.from_user.id)  # type: ignore[union-attr]
        if not reminders:
            await message.answer("Нет напоминаний.")
            return
        for r in reminders:
            card = reminder_card(r)
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Удалить", callback_data=f"rem_del:{r['id']}")]
                ]
            )
            await message.answer(card, reply_markup=kb)

    @router.callback_query(F.data.startswith("rem_del:"))
    async def delete_reminder(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        rem_id = int(callback.data.split(":")[1])
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data=f"rem_del_yes:{rem_id}"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="rem_del_no"),
                ]
            ]
        )
        await callback.message.edit_text("❓ Удалить напоминание?", reply_markup=kb)  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data.startswith("rem_del_yes:"))
    async def confirm_delete(callback: CallbackQuery) -> None:
        if not callback.data:
            return
        rem_id = int(callback.data.split(":")[1])
        await service.cancel_reminder(db, rem_id)
        await callback.message.edit_text("✅ Напоминание удалено.")  # type: ignore[union-attr]
        await callback.answer()

    @router.callback_query(F.data == "rem_del_no")
    async def cancel_delete(callback: CallbackQuery) -> None:
        await callback.message.edit_text("Оставлено.")  # type: ignore[union-attr]
        await callback.answer()

    @router.message(F.text == "📣 Рассылки")
    async def show_broadcasts(message: Message) -> None:
        broadcasts = await service.get_broadcasts(db)
        if not broadcasts:
            await message.answer("Рассылок не было.")
            return
        from src.core.ui import broadcast_card

        for bc in broadcasts[:5]:
            await message.answer(broadcast_card(bc))

    return router
