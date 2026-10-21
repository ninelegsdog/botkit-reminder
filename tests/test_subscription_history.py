"""F6: история подписки/отписки не теряется при удалении строки (152-ФЗ).

Факт плана bot-fixes F6: subscribe — upsert, unsubscribe — удаление строки:
история подписок непоследовательна (исчезает факт «был подписан»). План
предлагает два варианта, и первый (unsubscribe ставит is_active=False вместо
удаления) прямо противоречит решению владельца от 16.10 и обещанию каталога
«данные подписчика удаляются» (152-ФЗ, commit fd3aa66). Поэтому выбран
второй вариант: subscribe/unsubscribe пишут событие в журнал
`subscription_events` (аудит-лог, который README/SECURITY.md уже обещали, но
в коде не существовал), строка подписчика по-прежнему удаляется.

Негативный контроль (план: «вернуть удаление строки — тест истории падает»):
здесь адаптирован — убрать запись события в журнал → тест истории падает, а
тест 152-ФЗ (строка удаляется) остаётся зелёным.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.uow import UnitOfWork
from src.reminder.service import SubscriptionService


@pytest.fixture
async def session_factory(tmp_path):
    db = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory


async def test_subscribe_records_event(session_factory) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = SubscriptionService(uow)
        sub = await service.subscribe(42, "user", "Name")
        await session.commit()
        assert sub.is_active is True
        history = await service.subscription_history(42)
        assert [e.event for e in history] == ["subscribed"]


async def test_unsubscribe_deletes_row_and_records_event(session_factory) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = SubscriptionService(uow)
        await service.subscribe(42, "user", "Name")
        await session.commit()
        await service.unsubscribe(42)
        await session.commit()
        # 152-ФЗ: строка подписчика удалена — обещание каталога сохраняется.
        assert await service.get_subscriber(42) is None
        # История сохранена в журнале.
        history = await service.subscription_history(42)
        assert [e.event for e in history] == ["subscribed", "unsubscribed"]


async def test_history_visible_after_resubscribe(session_factory) -> None:
    """Приёмка F6: после подписки → отписки → подписки — одна активная
    подписка и видна история (3 события в хронологическом порядке)."""
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = SubscriptionService(uow)
        await service.subscribe(42, "user", "Name")
        await session.commit()
        await service.unsubscribe(42)
        await session.commit()
        await service.subscribe(42, "user2", "Name2")
        await session.commit()
        # Одна активная подписка — не дубликатов.
        sub = await service.get_subscriber(42)
        assert sub is not None and sub.is_active is True
        assert sub.username == "user2"
        # История сохранена — не исчезла вместе с удалённой строкой.
        history = await service.subscription_history(42)
        assert [e.event for e in history] == ["subscribed", "unsubscribed", "subscribed"]
        assert all(e.user_id == 42 for e in history)


async def test_total_unsubscribed_counts_events(session_factory) -> None:
    async with session_factory() as session:
        uow = UnitOfWork(session)
        service = SubscriptionService(uow)
        await service.subscribe(1, None, None)
        await service.subscribe(2, None, None)
        await session.commit()
        await service.unsubscribe(1)
        await session.commit()
        assert await service.total_unsubscribed() == 1
