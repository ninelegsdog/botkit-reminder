from __future__ import annotations

import pytest

from src.reminder import service


@pytest.mark.asyncio
async def test_subscribe(db):
    await service.subscribe(db, 123, "testuser", "Test")
    subscribers = await service.get_active_subscribers(db)
    assert len(subscribers) == 1


@pytest.mark.asyncio
async def test_unsubscribe(db):
    await service.subscribe(db, 123, "testuser", "Test")
    await service.unsubscribe(db, 123)
    subscribers = await service.get_active_subscribers(db)
    assert len(subscribers) == 0


@pytest.mark.asyncio
async def test_create_reminder_once(db):
    rem_id = await service.create_reminder(
        db, creator_id=123, reminder_type="once", fire_at="2026-01-01 09:00:00", text_content="Test"
    )
    assert rem_id > 0


@pytest.mark.asyncio
async def test_create_reminder_recurring(db):
    rem_id = await service.create_reminder(
        db, creator_id=123, reminder_type="recurring", fire_at="09:00:00",
        text_content="Weekly", cron_day=0
    )
    assert rem_id > 0


@pytest.mark.asyncio
async def test_get_user_reminders(db):
    await service.create_reminder(
        db, creator_id=123, reminder_type="once", fire_at="2026-01-01 09:00:00", text_content="Test"
    )
    reminders = await service.get_user_reminders(db, 123)
    assert len(reminders) == 1


@pytest.mark.asyncio
async def test_cancel_reminder(db):
    rem_id = await service.create_reminder(
        db, creator_id=123, reminder_type="once", fire_at="2026-01-01 09:00:00", text_content="Test"
    )
    await service.cancel_reminder(db, rem_id)
    reminders = await service.get_user_reminders(db, 123)
    assert len(reminders) == 0


@pytest.mark.asyncio
async def test_create_broadcast(db):
    bc_id = await service.create_broadcast(db, text_content="Hello", segment="all")
    assert bc_id > 0


@pytest.mark.asyncio
async def test_get_broadcasts(db):
    await service.create_broadcast(db, text_content="Hello", segment="all")
    broadcasts = await service.get_broadcasts(db)
    assert len(broadcasts) == 1
