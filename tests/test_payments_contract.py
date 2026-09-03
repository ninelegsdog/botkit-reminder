"""Contract tests for payments (Mock) — reminder."""
from __future__ import annotations

import pytest

from src.core.payments import MockAdapter


@pytest.mark.asyncio
async def test_mock_create_invoice() -> None:
    provider = MockAdapter()
    invoice = await provider.create_invoice(user_id=123, amount=100, payload="pay_123")
    assert invoice is not None
    assert isinstance(invoice, dict) or hasattr(invoice, "provider")


def test_mock_adapter_is_payment_provider() -> None:
    from src.core.payments import PaymentProvider

    provider = MockAdapter()
    assert isinstance(provider, PaymentProvider)
