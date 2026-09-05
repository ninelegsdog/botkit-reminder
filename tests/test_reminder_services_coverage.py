"""Coverage boost for reminder services (send paths, retries, broadcast)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter

from src.reminder.models import (
    Broadcast,
    BroadcastStatus,
    Reminder,
    ReminderRecipient,
    ReminderStatus,
    ReminderType,
    Subscriber,
)
from src.reminder.service import (
    BroadcastService,
    ReminderService,
    SubscriptionService,
)


def _fake_uow() -> Any:
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    result = MagicMock()
    result.scalar_one = MagicMock(return_value=5)
    result.scalar_one_or_none = MagicMock(return_value=None)
    result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    session.execute = AsyncMock(return_value=result)
    uow = MagicMock()
    uow.session = session
    return uow


def _reminder(**kwargs: Any) -> Reminder:
    fields: dict[str, Any] = {
        "creator_id": 1,
        "type": ReminderType.once,
        "text": "remind me",
    }
    fields.update(kwargs)
    return Reminder(**fields)


def _recipient(user_id: int) -> ReminderRecipient:
    return ReminderRecipient(reminder_id=1, user_id=user_id)


def _subscriber(user_id: int, is_active: bool = True) -> Subscriber:
    return Subscriber(user_id=user_id, username=f"u{user_id}", name="Name", is_active=is_active)


class TestReminderService:

    async def test_send_reminder_no_bot(self):
        uow = _fake_uow()
        service = ReminderService(uow)
        await service.send_reminder(_reminder(id=1))
        uow.session.execute.assert_not_called()

    async def test_send_reminder_delivered_and_failed(self):
        uow = _fake_uow()
        bot = MagicMock()
        bot.send_message = AsyncMock()
        bot.send_message.side_effect = [None, RuntimeError("boom")]
        recipients = [_recipient(100), _recipient(200)]
        uow.session.execute.return_value.scalars.return_value.all.return_value = recipients
        service = ReminderService(uow, bot=bot)
        await service.send_reminder(_reminder(id=1, text="⏰ hello"))
        assert recipients[0].status == BroadcastStatus.delivered
        assert recipients[0].delivered_at is not None
        assert recipients[1].status == BroadcastStatus.failed
        uow.session.flush.assert_awaited_once()

    async def test_get_recipients(self):
        uow = _fake_uow()
        recipients = [_recipient(100)]
        uow.session.execute.return_value.scalars.return_value.all.return_value = recipients
        service = ReminderService(uow)
        result = await service._get_recipients(1)
        assert result == recipients

    async def test_add_recipient(self):
        uow = _fake_uow()
        service = ReminderService(uow)
        rr = await service.add_recipient(1, 200)
        assert rr.user_id == 200
        assert rr.reminder_id == 1

    async def test_cancel_reminder_found(self):
        uow = _fake_uow()
        reminder = _reminder(id=1)
        uow.session.execute.return_value.scalar_one_or_none.return_value = reminder
        service = ReminderService(uow)
        await service.cancel_reminder(1)
        assert reminder.status == ReminderStatus.cancelled
        assert reminder.is_active is False

    async def test_cancel_reminder_missing(self):
        uow = _fake_uow()
        service = ReminderService(uow)
        await service.cancel_reminder(999)
        assert True

    async def test_get_subscriber(self):
        uow = _fake_uow()
        sub = _subscriber(100)
        uow.session.execute.return_value.scalar_one_or_none.return_value = sub
        service = ReminderService(uow)
        assert await service.get_subscriber(100) is sub


class TestBroadcastService:

    async def test_create_broadcast(self):
        uow = _fake_uow()
        service = BroadcastService(uow)
        bc = await service.create_broadcast("hello", segment="active")
        assert bc.text == "hello"
        assert bc.segment == "active"

    async def test_send_broadcast_missing(self):
        uow = _fake_uow()
        service = BroadcastService(uow, bot=MagicMock())
        await service.send_broadcast(999)
        uow.session.execute.return_value.scalars.return_value.all.assert_not_called()
        assert True

    async def test_send_broadcast_no_bot(self):
        uow = _fake_uow()
        broadcast = Broadcast(text="x", segment="active")
        subscribers = [_subscriber(100), _subscriber(200, is_active=False)]
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=broadcast)
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=subscribers)))
        uow.session.execute = AsyncMock(return_value=result)
        service = BroadcastService(uow)
        await service.send_broadcast(1)
        assert broadcast.total == 2
        assert broadcast.delivered == 1
        assert broadcast.failed == 0
        assert broadcast.unsubscribed == 1
        assert broadcast.sent_at is not None

    async def test_send_broadcast_with_bot_mixed(self):
        uow = _fake_uow()
        broadcast = Broadcast(text="x", segment="active")
        subscribers = [
            _subscriber(100, is_active=True),
            _subscriber(200, is_active=False),
            _subscriber(300, is_active=True),
            _subscriber(400, is_active=True),
        ]
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=broadcast)
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=subscribers)))
        uow.session.execute = AsyncMock(return_value=result)
        bot = MagicMock()
        bot.send_message = AsyncMock()
        bot.send_message.side_effect = [None, None, RuntimeError("boom"), None]
        service = BroadcastService(uow, bot=bot)
        await service.send_broadcast(1)
        assert broadcast.total == 4
        assert broadcast.delivered == 2
        assert broadcast.failed == 1
        assert broadcast.unsubscribed == 1
        assert broadcast.sent_at is not None
        assert uow.session.flush.await_count >= 2

    async def test_send_broadcast_empty(self):
        uow = _fake_uow()
        broadcast = Broadcast(text="x", segment="active")
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=broadcast)
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        uow.session.execute = AsyncMock(return_value=result)
        service = BroadcastService(uow, bot=MagicMock())
        await service.send_broadcast(1)
        assert broadcast.total == 0
        assert broadcast.sent_at is not None

    async def test_send_with_retry_success_first(self):
        service = BroadcastService(_fake_uow(), bot=MagicMock())
        bot = MagicMock()
        bot.send_message = AsyncMock(return_value=None)
        await service._send_with_retry(bot, 100, "hi")
        bot.send_message.assert_awaited_once()

    async def test_send_with_retry_after_flood(self):
        service = BroadcastService(_fake_uow(), bot=MagicMock())
        bot = MagicMock()
        bot.send_message = AsyncMock()
        bot.send_message.side_effect = [
            TelegramRetryAfter(method="sendMessage", message="flood", retry_after=0),
            None,
        ]
        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            await service._send_with_retry(bot, 100, "hi")
        assert bot.send_message.await_count == 2
        mock_sleep.assert_awaited_once()

    async def test_send_with_retry_after_network(self):
        service = BroadcastService(_fake_uow(), bot=MagicMock())
        bot = MagicMock()
        bot.send_message = AsyncMock()
        bot.send_message.side_effect = [
            TelegramNetworkError(method="sendMessage", message="net"),
            TelegramNetworkError(method="sendMessage", message="net"),
            None,
        ]
        with patch("asyncio.sleep", new=AsyncMock()):
            await service._send_with_retry(bot, 100, "hi")
        assert bot.send_message.await_count == 3

    async def test_send_with_retry_exhausted(self):
        service = BroadcastService(_fake_uow(), bot=MagicMock())
        bot = MagicMock()
        bot.send_message = AsyncMock(
            side_effect=TelegramNetworkError(method="sendMessage", message="net")
        )
        with patch("asyncio.sleep", new=AsyncMock()), pytest.raises(RuntimeError):
            await service._send_with_retry(bot, 100, "hi")
        assert bot.send_message.await_count == 3


class TestSubscriptionService:

    async def test_subscribe_new(self):
        uow = _fake_uow()
        service = SubscriptionService(uow)
        sub = await service.subscribe(100, "u100", "Name")
        assert sub.user_id == 100
        assert sub.username == "u100"
        uow.session.add.assert_called_once()

    async def test_subscribe_existing(self):
        uow = _fake_uow()
        existing = _subscriber(100, is_active=False)
        uow.session.execute.return_value.scalar_one_or_none.return_value = existing
        service = SubscriptionService(uow)
        sub = await service.subscribe(100, "new_name", "New")
        assert sub is existing
        assert existing.is_active is True
        assert existing.username == "new_name"

    async def test_unsubscribe_existing(self):
        uow = _fake_uow()
        existing = _subscriber(100, is_active=True)
        uow.session.execute.return_value.scalar_one_or_none.return_value = existing
        service = SubscriptionService(uow)
        await service.unsubscribe(100)
        assert existing.is_active is False

    async def test_unsubscribe_missing(self):
        uow = _fake_uow()
        service = SubscriptionService(uow)
        await service.unsubscribe(999)
        uow.session.execute.assert_awaited_once()

    async def test_get_subscriber(self):
        uow = _fake_uow()
        sub = _subscriber(100)
        uow.session.execute.return_value.scalar_one_or_none.return_value = sub
        service = SubscriptionService(uow)
        assert await service.get_subscriber(100) is sub