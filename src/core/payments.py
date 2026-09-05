"""Payments shim — re-exports botkit_core.payments."""
from __future__ import annotations

from botkit_core.payments import MockPaymentProvider, PaymentProvider, YooKassaPaymentProvider, create_payment_provider

__all__ = [
    "MockPaymentProvider",
    "PaymentProvider",
    "YooKassaPaymentProvider",
    "create_payment_provider",
]
