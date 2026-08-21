from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏰ Мои напоминания"), KeyboardButton(text="➕ Добавить")],
            [KeyboardButton(text="📣 Рассылки")],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📣 Рассылка"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="👥 Подписчики")],
        ],
        resize_keyboard=True,
    )
