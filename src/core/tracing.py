"""Tracing shim — re-exports botkit_core.tracing + aiogram middleware."""
from __future__ import annotations

from botkit_core.tracing import (
    TracingMiddleware,
    get_current_span,
    set_current_span,
    setup_tracing,
)

__all__ = [
    "TracingMiddleware",
    "get_current_span",
    "set_current_span",
    "setup_tracing",
]
