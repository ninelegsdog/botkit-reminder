from __future__ import annotations

from typing import Any

from src.core.uow import UnitOfWork


class DIContainer:
    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def register(self, name: str, factory: Any) -> None:
        self._services[name] = factory

    def get(self, name: str) -> Any:
        if name not in self._services:
            raise KeyError(f"Service '{name}' not registered in DI container")
        return self._services[name]

    def uow(self) -> UnitOfWork:
        return UnitOfWork()


container = DIContainer()
