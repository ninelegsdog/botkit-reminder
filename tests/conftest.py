"""Shared fixtures for reminder tests + testcontainers."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:ABC")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "secret")
os.environ.setdefault("ADMIN_IDS", "123")
os.environ.setdefault("ADMIN_PASSWORD_HASH", "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918")

from src.core.bot_factory import AppState


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def postgres_container() -> Any:
    """PostgreSQL 16 container for integration tests."""
    from testcontainers.community.postgres import PostgresContainer
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def redis_container() -> Any:
    """Redis 7 container for integration tests."""
    from testcontainers.community.redis import RedisContainer
    container = RedisContainer("redis:7-alpine")
    container.start()
    yield container
    container.stop()


@pytest.fixture
def postgres_url(postgres_container) -> str:
    """Get PostgreSQL connection URL."""
    return postgres_container.get_connection_url().replace("postgresql+psycopg2", "postgresql+asyncpg")


@pytest.fixture
def redis_url(redis_container) -> str:
    """Get Redis connection URL."""
    return f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"


@pytest.fixture
async def db_engine(postgres_url: str):
    """Create async SQLAlchemy engine."""
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(postgres_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create database session for tests."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def redis_client(redis_url: str):
    """Create Redis client for tests."""
    import redis.asyncio as redis
    client = redis.from_url(redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def tmp_db() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "test.db")
        yield db


@pytest.fixture
def app_state() -> Any:
    return AppState()


_PAYLOADS_DIR = Path(__file__).parent / "fixtures" / "payloads"


@pytest.fixture
def load_payload() -> Any:
    """Load a JSON Telegram-update fixture from tests/fixtures/payloads/."""

    def _load(name: str) -> dict[str, Any]:
        return json.loads((_PAYLOADS_DIR / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    return _load


def pytest_collection_modifyitems(config: Any, items: Any) -> None:
    """Handle integration tests and real Telegram tests."""
    run_integration = config.getoption("--run-integration", default=False)
    for item in items:
        # Handle integration tests
        if "integration" in item.keywords:
            if not run_integration:
                item.add_marker(pytest.mark.skip(reason="need --run-integration option to run"))
            continue
        # Handle real Telegram tests
        path = getattr(item, "path", None)
        fname = Path(path).name if path else ""
        is_req_file = fname == "test_e2e.py"
        if "req" in item.keywords or is_req_file:
            if os.getenv("RUN_TELEGRAM_E2E") != "1":
                item.add_marker(
                    pytest.mark.skip(reason="set RUN_TELEGRAM_E2E=1 to run real Telegram tests")
                )
        elif "no_req" not in item.keywords:
            item.add_marker(pytest.mark.no_req)


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests with testcontainers",
    )
