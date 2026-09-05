"""Coverage boost for reminder handlers (stateful flows + admin)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Chat, User

from src.core.auth import admin_gate
from src.reminder.handlers import create_router
from src.reminder.models import ReminderType


def _user(uid: int = 456) -> User:
    return User(id=uid, is_bot=False, first_name="Test User", username="test_user")


def _make_message(
    uid: int = 456, mid: int = 1, text: str | None = None
) -> Any:
    msg = MagicMock()
    msg.bot = MagicMock()
    msg.chat = Chat(id=1, type="private")
    msg.from_user = _user(uid)
    msg.message_id = mid
    msg.text = text
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    return msg


def _make_callback(data: str, uid: int = 456) -> Any:
    cq = MagicMock()
    cq.bot = MagicMock()
    cq.data = data
    cq.from_user = _user(uid)
    cq.message = _make_message(uid=uid, text=None)
    cq.answer = AsyncMock()
    return cq


def _find(router: Any, attr: str, name: str) -> Any:
    for h in getattr(router, attr).handlers:
        cb = h.callback
        if hasattr(cb, "__name__") and cb.__name__ == name:
            return cb
    raise AssertionError(f"handler {name!r} not found")


@pytest.fixture
def fsm() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=0, chat_id=1, user_id=456),
    )


@pytest.fixture
def router() -> Any:
    return create_router()


@pytest.fixture
def fake_uow() -> Any:
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
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.session = session
    return uow


@pytest.fixture
def patched_uow(fake_uow: Any) -> Any:
    with patch("src.reminder.handlers.UnitOfWork", return_value=fake_uow):
        yield fake_uow


class TestPublicHandlers:

    async def test_cmd_start(self, router):
        handler = _find(router, "message", "cmd_start")
        msg = _make_message(text="/start")
        await handler(msg)
        msg.answer.assert_awaited_once()
        assert "Подпишитесь на напоминания" in msg.answer.await_args[0][0]

    async def test_subscribe(self, router, patched_uow):
        handler = _find(router, "message", "subscribe")
        msg = _make_message(text="🔔 Подписаться")
        await handler(msg)
        msg.answer.assert_awaited_once()
        assert "Вы подписаны" in msg.answer.await_args[0][0]

    async def test_subscribe_no_user(self, router, patched_uow):
        handler = _find(router, "message", "subscribe")
        msg = _make_message(text="🔔 Подписаться")
        msg.from_user = None
        await handler(msg)
        msg.answer.assert_not_awaited()

    async def test_unsubscribe(self, router, patched_uow):
        handler = _find(router, "message", "unsubscribe")
        msg = _make_message(text="🔕 Отписаться")
        await handler(msg)
        msg.answer.assert_awaited_once()
        assert "Вы отписались" in msg.answer.await_args[0][0]

    async def test_unsubscribe_no_user(self, router, patched_uow):
        handler = _find(router, "message", "unsubscribe")
        msg = _make_message(text="🔕 Отписаться")
        msg.from_user = None
        await handler(msg)
        msg.answer.assert_not_awaited()

    async def test_add_reminder_start(self, router):
        handler = _find(router, "message", "add_reminder_start")
        msg = _make_message(text="➕ Добавить")
        await handler(msg, MagicMock())
        msg.answer.assert_awaited_once()
        assert "Выберите тип напоминания" in msg.answer.await_args[0][0]

    async def test_once_type(self, router, fsm):
        handler = _find(router, "callback_query", "once_type")
        cb = _make_callback("rem:type:once")
        await handler(cb, fsm)
        data = await fsm.get_data()
        assert data["type"] == ReminderType.once.value
        assert await fsm.get_state() == "reminder:text"
        cb.message.edit_text.assert_awaited_with("Введите текст напоминания:")

    async def test_recurring_type(self, router, fsm):
        handler = _find(router, "callback_query", "recurring_type")
        cb = _make_callback("rem:type:recurring")
        await handler(cb, fsm)
        data = await fsm.get_data()
        assert data["type"] == ReminderType.recurring.value
        cb.message.edit_text.assert_awaited_once()
        args, kwargs = cb.message.edit_text.await_args
        assert "Выберите день недели" in args[0]
        assert "reply_markup" in kwargs

    async def test_day_selected(self, router, fsm):
        handler = _find(router, "callback_query", "day_selected")
        cb = _make_callback("rem:day:2")
        await handler(cb, fsm)
        data = await fsm.get_data()
        assert data["cron_day"] == "2"
        assert await fsm.get_state() == "reminder:text"

    async def test_text_entered_recurring(self, router, fsm):
        await fsm.update_data(type=ReminderType.recurring.value)
        handler = _find(router, "message", "text_entered")
        msg = _make_message(text="  Кружка  ")
        await handler(msg, fsm)
        data = await fsm.get_data()
        assert data["text"] == "Кружка"
        assert await fsm.get_state() == "reminder:time"
        msg.answer.assert_awaited_with("Введите время ЧЧ:ММ")

    async def test_text_entered_once(self, router, fsm):
        await fsm.update_data(type=ReminderType.once.value)
        handler = _find(router, "message", "text_entered")
        msg = _make_message(text="hello")
        await handler(msg, fsm)
        assert await fsm.get_state() == "reminder:date"
        msg.answer.assert_awaited_with("Введите дату в формате ДД.ММ.ГГГГ")

    async def test_text_entered_no_text(self, router, fsm):
        handler = _find(router, "message", "text_entered")
        msg = _make_message(text=None)
        await handler(msg, fsm)
        msg.answer.assert_not_awaited()

    async def test_date_entered_valid(self, router, fsm):
        handler = _find(router, "message", "date_entered")
        msg = _make_message(text="05.09.2026")
        await handler(msg, fsm)
        data = await fsm.get_data()
        assert data["fire_at"] == "2026-09-05"
        assert await fsm.get_state() == "reminder:time"

    async def test_date_entered_invalid(self, router, fsm):
        handler = _find(router, "message", "date_entered")
        msg = _make_message(text="banana")
        await handler(msg, fsm)
        msg.answer.assert_awaited_with("Неверный формат. Введите ДД.ММ.ГГГГ")
        assert await fsm.get_state() is None

    async def test_time_entered_bad_format(self, router, fsm):
        handler = _find(router, "message", "time_entered")
        msg = _make_message(text="abc")
        await handler(msg, fsm)
        msg.answer.assert_awaited_with("Неверный формат. Введите ЧЧ:ММ")

    async def test_time_entered_missing_text(self, router, fsm):
        await fsm.update_data(type=ReminderType.once.value)
        handler = _find(router, "message", "time_entered")
        msg = _make_message(text="10:30")
        await handler(msg, fsm)
        msg.answer.assert_awaited_with("Сначала введите текст напоминания")
        assert await fsm.get_state() is None

    async def test_time_entered_missing_date(self, router, fsm):
        await fsm.update_data(type=ReminderType.once.value, text="hello")
        handler = _find(router, "message", "time_entered")
        msg = _make_message(text="10:30")
        await handler(msg, fsm)
        msg.answer.assert_awaited_with("Сначала выберите дату")
        assert await fsm.get_state() is None

    async def test_time_entered_once(self, router, fsm, patched_uow):
        await fsm.update_data(
            type=ReminderType.once.value, text="hello", fire_at="2026-09-05"
        )
        handler = _find(router, "message", "time_entered")
        msg = _make_message(text="10:30")
        await handler(msg, fsm)
        msg.answer.assert_awaited_once()
        assert "Напоминание создано" in msg.answer.await_args[0][0]
        assert await fsm.get_state() is None

    async def test_time_entered_recurring(self, router, fsm, patched_uow):
        await fsm.update_data(
            type=ReminderType.recurring.value, text="📣 обзор", cron_day="2"
        )
        handler = _find(router, "message", "time_entered")
        msg = _make_message(text="09:00")
        await handler(msg, fsm)
        msg.answer.assert_awaited_once()
        assert "Напоминание создано" in msg.answer.await_args[0][0]

    async def test_my_reminders_empty(self, router, fake_uow):
        handler = _find(router, "message", "my_reminders")
        msg = _make_message(text="⏰ Мои напоминания")
        with patch("src.reminder.handlers.UnitOfWork", return_value=fake_uow):
            await handler(msg)
        msg.answer.assert_awaited_once()
        assert "Нет напоминаний" in msg.answer.await_args[0][0]

    async def test_my_reminders_with_items(self, router, fake_uow):
        handler = _find(router, "message", "my_reminders")
        msg = _make_message(text="⏰ Мои напоминания")
        once = MagicMock()
        once.id = 10
        once.type = ReminderType.once
        once.fire_at = datetime(2026, 9, 5, 10, 0, tzinfo=UTC)
        once.cron_day = None
        once.text = "встреча"
        recurring = MagicMock()
        recurring.id = 11
        recurring.type = ReminderType.recurring
        recurring.fire_at = None
        recurring.cron_day = "1"
        recurring.text = "обзор"
        fake_uow.session.execute.return_value.scalars.return_value.all.return_value = [once, recurring]
        with patch("src.reminder.handlers.UnitOfWork", return_value=fake_uow):
            await handler(msg)
        msg.answer.assert_awaited_once()
        text = msg.answer.await_args[0][0]
        assert "#10 once 05.09.2026 10:00" in text
        assert "#11 recurring 1" in text

    async def test_my_reminders_no_user(self, router, fake_uow):
        handler = _find(router, "message", "my_reminders")
        msg = _make_message(text="⏰ Мои напоминания")
        msg.from_user = None
        with patch("src.reminder.handlers.UnitOfWork", return_value=fake_uow):
            await handler(msg)
        msg.answer.assert_not_awaited()

    async def test_delete_prompt(self, router):
        handler = _find(router, "callback_query", "delete_reminder_prompt")
        cb = _make_callback("rem:delete:5")
        await handler(cb)
        cb.message.edit_text.assert_awaited_once()
        args, kwargs = cb.message.edit_text.await_args
        assert "Удалить" in args[0]
        assert "reply_markup" in kwargs

    async def test_delete_confirm(self, router, patched_uow):
        handler = _find(router, "callback_query", "delete_reminder_confirm")
        cb = _make_callback("rem:confirm:delete:5")
        await handler(cb)
        cb.message.edit_text.assert_awaited_with("✅ Напоминание удалено")
        cb.answer.assert_awaited_once()

    async def test_delete_cancel(self, router):
        handler = _find(router, "callback_query", "delete_cancel")
        cb = _make_callback("rem:cancel")
        await handler(cb)
        cb.message.edit_text.assert_awaited_with("❌ Отменено")
        cb.answer.assert_awaited_once()


class TestAdminHandlers:

    @pytest.fixture(autouse=True)
    def _admin_login(self):
        admin_gate.logout(456)
        admin_gate.login(456)
        yield
        admin_gate.logout(456)

    async def test_broadcasts(self, router, fsm):
        handler = _find(router, "message", "broadcasts")
        msg = _make_message(text="📣 Рассылки")
        await handler(msg, fsm)
        assert await fsm.get_state() == "broadcast.text"
        msg.answer.assert_awaited_with("Введите текст рассылки:")

    async def test_broadcast_text(self, router, fsm, patched_uow):
        await fsm.set_state("broadcast.text")
        handler = _find(router, "message", "broadcast_text")
        msg = _make_message(text="Новость дня")
        await handler(msg, fsm)
        assert await fsm.get_state() is None
        msg.answer.assert_awaited_once()
        assert "Рассылка отправлена" in msg.answer.await_args[0][0]

    async def test_broadcast_text_no_text(self, router, fsm, patched_uow):
        handler = _find(router, "message", "broadcast_text")
        msg = _make_message(text=None)
        await handler(msg, fsm)
        msg.answer.assert_not_awaited()

    async def test_admin_entry(self, router, fsm):
        handler = _find(router, "message", "admin_entry")
        msg = _make_message(text="/admin")
        await handler(msg, fsm)
        assert await fsm.get_state() == "admin:password"
        msg.answer.assert_awaited_with("Введите пароль:")

    async def test_admin_password_ok(self, router, fsm):
        handler = _find(router, "message", "admin_password")
        msg = _make_message(text="secret")
        with patch("src.core.auth.verify_password", return_value=True):
            await handler(msg, fsm)
        assert await fsm.get_state() is None
        assert admin_gate.is_authorized(456)
        msg.answer.assert_awaited_once()

    async def test_admin_password_wrong(self, router, fsm):
        handler = _find(router, "message", "admin_password")
        msg = _make_message(text="nope")
        with patch("src.core.auth.verify_password", return_value=False):
            await handler(msg, fsm)
        msg.answer.assert_awaited_with("❌ Неверный пароль")

    async def test_admin_password_no_user(self, router, fsm):
        handler = _find(router, "message", "admin_password")
        msg = _make_message(text="secret")
        msg.from_user = None
        with patch("src.core.auth.verify_password", return_value=True):
            await handler(msg, fsm)
        msg.answer.assert_not_awaited()

    async def test_admin_stats(self, router, fake_uow):
        handler = _find(router, "message", "admin_stats")
        msg = _make_message(text="📊 Статистика")
        with patch("src.reminder.handlers.UnitOfWork", return_value=fake_uow):
            await handler(msg)
        msg.answer.assert_awaited_once()
        text = msg.answer.await_args[0][0]
        assert "Подписчиков: 5" in text
        assert "Напоминаний: 5" in text

    async def test_admin_subscribers(self, router, fake_uow):
        handler = _find(router, "message", "admin_subscribers")
        msg = _make_message(text="👥 Подписчики")
        sub1 = MagicMock()
        sub1.user_id = 10
        sub1.name = "Alice"
        sub1.username = "alice"
        sub2 = MagicMock()
        sub2.user_id = 20
        sub2.name = None
        sub2.username = None
        fake_uow.session.execute.return_value.scalars.return_value.all.return_value = [sub1, sub2]
        with patch("src.reminder.handlers.UnitOfWork", return_value=fake_uow):
            await handler(msg)
        msg.answer.assert_awaited_once()
        text = msg.answer.await_args[0][0]
        assert "10" in text
        assert "alice" in text

    async def test_admin_subscribers_empty(self, router, fake_uow):
        handler = _find(router, "message", "admin_subscribers")
        msg = _make_message(text="👥 Подписчики")
        with patch("src.reminder.handlers.UnitOfWork", return_value=fake_uow):
            await handler(msg)
        msg.answer.assert_awaited_with("Нет подписчиков")