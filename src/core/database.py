from __future__ import annotations

import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.asyncio import async_sessionmaker as AsyncSessionMaker
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def async_session(self) -> AsyncSessionMaker[AsyncSession]:
        return self._session_factory

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def dispose(self) -> None:
        await self._engine.dispose()


db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def ensure_wal(db_file: Path) -> None:
    if db_file.suffix not in (".db", ".sqlite"):
        return
    try:
        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.close()
    except Exception:
        pass


def backup_database(dest_dir: Path) -> str | None:
    db_file = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    if not db_file.exists():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = __import__("datetime").datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{db_file.name}.{stamp}.backup"
    try:
        import shutil
        shutil.copy2(db_file, dest)
        ensure_wal(dest)
        return str(dest)
    except Exception:
        return None
