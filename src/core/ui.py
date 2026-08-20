from __future__ import annotations

import html
from aiogram.types import InlineKeyboardMarkup


def escape(text: str) -> str:
    return html.escape(text)


def truncate(text: str, limit: int = 4096) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


async def safe_edit_text(message, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    safe = truncate(text)
    if reply_markup is None:
        await message.edit_text(safe)
    else:
        await message.edit_text(safe, reply_markup=reply_markup)
