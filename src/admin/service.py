from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.uow import UnitOfWork
from src.reminder.models import Reminder, Subscriber


class AdminService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    @property
    def session(self) -> AsyncSession:
        return self._uow.session

    async def stats(self) -> dict[str, int]:
        stmt = select(func.count()).select_from(Subscriber).where(Subscriber.is_active)
        result = await self.session.execute(stmt)
        subs = result.scalar_one()
        stmt2 = select(func.count()).select_from(Reminder)
        result2 = await self.session.execute(stmt2)
        reminders = result2.scalar_one()
        return {"subscribers": subs, "reminders": reminders}

    async def subscribers(self) -> Sequence[Subscriber]:
        stmt = select(Subscriber).where(Subscriber.is_active)
        result = await self.session.execute(stmt)
        return result.scalars().all()
