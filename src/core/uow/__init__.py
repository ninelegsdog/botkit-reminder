from __future__ import annotations

from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session


class UnitOfWork:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UoW is not initialized. Use 'async with uow:' context manager.")
        return self._session

    async def __aenter__(self) -> Self:
        if self._session is None:
            self._session = async_session()
            await self._session.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._owns_session and self._session is not None:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
