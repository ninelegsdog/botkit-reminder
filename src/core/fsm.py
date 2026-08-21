from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ReminderOnce(StatesGroup):
    entering_date = State()
    entering_time = State()
    entering_text = State()
    confirming = State()


class ReminderRecurring(StatesGroup):
    choosing_day = State()
    entering_time = State()
    entering_text = State()
    confirming = State()


class BroadcastCreate(StatesGroup):
    entering_text = State()
    choosing_segment = State()
    confirming = State()


class AdminAuth(StatesGroup):
    waiting_password = State()
