from __future__ import annotations

import html
from typing import Any


def escape(text: str | None) -> str:
    return html.escape(str(text)) if text else ""


def reminder_card(reminder: dict[str, Any]) -> str:
    rtype = str(reminder.get("type", "once"))
    type_label = "🔸 Одноразовое" if rtype == "once" else "🔁 Повторяющееся"
    status = str(reminder.get("is_active", 1))
    status_label = "✅ Активно" if status == "1" else "❌ Отменено"
    return (
        f"⏰ Напоминание #{reminder['id']}\n"
        f"Тип: {type_label}\n"
        f"Текст: {escape(str(reminder.get('text', '')))}\n"
        f"Статус: {status_label}"
    )


def broadcast_card(broadcast: dict[str, Any]) -> str:
    return (
        f"📣 Рассылка #{broadcast['id']}\n"
        f"Текст: {escape(str(broadcast.get('text', '')))}\n"
        f"Доставлено: {broadcast.get('delivered', 0)}/{broadcast.get('total', 0)}"
    )
