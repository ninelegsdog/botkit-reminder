from __future__ import annotations

import pytest

from src.core.ui import reminder_card
from src.reminder import service


@pytest.mark.asyncio
async def test_full_reminder_flow(db):
    await service.subscribe(db, 111, "user1", "User One")
    rem_id = await service.create_reminder(
        db, creator_id=111, reminder_type="once",
        fire_at="2026-01-01 09:00:00", text_content="Meeting"
    )
    assert rem_id > 0

    reminders = await service.get_user_reminders(db, 111)
    assert len(reminders) == 1

    await service.cancel_reminder(db, rem_id)
    reminders = await service.get_user_reminders(db, 111)
    assert len(reminders) == 0


@pytest.mark.asyncio
async def test_broadcast_flow(db):
    await service.subscribe(db, 111, "user1", "User One")
    await service.subscribe(db, 222, "user2", "User Two")
    bc_id = await service.create_broadcast(db, text_content="Hello", segment="all")
    assert bc_id > 0

    subscribers = await service.get_active_subscribers(db)
    assert len(subscribers) == 2


@pytest.mark.asyncio
async def test_reminder_card_html():
    card = reminder_card({
        "id": 1,
        "type": "once",
        "text": "Test <script>",
        "is_active": 1,
    })
    assert "<script>" not in card
    assert "Напоминание #1" in card
