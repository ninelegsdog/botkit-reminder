from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.reminder.models import Broadcast, BroadcastRecipient, Reminder, Subscriber


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def stats(self) -> dict[str, int]:
        stmt = select(func.count()).select_from(Subscriber).where(Subscriber.is_active == True)
        result = await self.session.execute(stmt)
        subs = result.scalar_one()
        stmt2 = select(func.count()).select_from(Reminder)
        result2 = await self.session.execute(stmt2)
        reminders = result2.scalar_one()
        return {"subscribers": subs, "reminders": reminders}

    async def subscribers(self) -> Sequence[Subscriber]:
        stmt = select(Subscriber).where(Subscriber.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalars().all()
