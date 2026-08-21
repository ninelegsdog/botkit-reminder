from __future__ import annotations

import asyncio

from aiogram import Bot

from src.core.database import Database
from src.reminder import service


async def reminder_loop(bot: Bot, db: Database, interval: int = 30) -> None:
    while True:
        try:
            due = await service.get_due_reminders(db)
            for reminder in due:
                subscribers = await service.get_active_subscribers(db)
                for sub in subscribers:
                    try:
                        await bot.send_message(
                            sub["user_id"],
                            f"⏰ Напоминание: {reminder['text']}",
                        )
                        await service.add_reminder_recipient(
                            db, int(reminder["id"]), sub["user_id"]
                        )
                        await service.mark_recipient_delivered(
                            db, int(reminder["id"]), sub["user_id"]
                        )
                    except Exception:
                        pass
                if reminder["type"] == "once":
                    await service.mark_reminder_done(db, int(reminder["id"]))
        except Exception:
            pass
        await asyncio.sleep(interval)
