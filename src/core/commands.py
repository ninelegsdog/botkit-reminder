from __future__ import annotations

from contextlib import suppress

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

from src.core.config import settings

BOT_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="help", description="Справка"),
    BotCommand(command="add", description="Добавить напоминание"),
    BotCommand(command="list", description="Мои напоминания"),
    BotCommand(command="subscribe", description="Подписаться на рассылки"),
    BotCommand(command="unsubscribe", description="Отписаться от рассылок"),
    BotCommand(command="cancel", description="Отмена текущего действия"),
]


async def set_commands(bot: Bot) -> None:
    if settings.telegram_bot_token:
        with suppress(Exception):
            await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeDefault())
