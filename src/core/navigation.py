from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def compose_message(title: str, body: str) -> str:
    return f"<b>{title}</b>\n\n{body}"


def nav_header(*parts: str) -> str:
    return " › ".join(parts)


def reply_menu(*buttons: str) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for text in buttons:
        builder.add(types.KeyboardButton(text=text))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def inline_buttons(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in rows:
        for text, callback in row:
            builder.add(types.InlineKeyboardButton(text=text, callback_data=callback))
    builder.adjust(2)
    return builder.as_markup()
