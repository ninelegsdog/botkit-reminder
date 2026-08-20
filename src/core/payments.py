from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class PaymentStatus(str, Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class PaymentProvider(ABC):
    @abstractmethod
    async def create_invoice(self, user_id: int, amount: int, payload: str) -> dict[str, Any]:
        ...

    @abstractmethod
    async def confirm(self, payload: str) -> PaymentStatus:
        ...

    @abstractmethod
    async def subscription_status(self, user_id: int) -> PaymentStatus:
        ...


@dataclass
class Invoice:
    provider: str
    external_id: str
    amount: int
    currency: str
    payload: str


class MockAdapter(PaymentProvider):
    async def create_invoice(self, user_id: int, amount: int, payload: str) -> dict[str, Any]:
        return Invoice(provider="mock", external_id=f"mock-{payload}", amount=amount, currency="XTR", payload=payload).__dict__

    async def confirm(self, payload: str) -> PaymentStatus:
        return PaymentStatus.succeeded

    async def subscription_status(self, user_id: int) -> PaymentStatus:
        return PaymentStatus.succeeded


_adapter: PaymentProvider = MockAdapter()


def get_payment_provider() -> PaymentProvider:
    return _adapter


def set_payment_provider(provider: PaymentProvider) -> None:
    global _adapter
    _adapter = provider
