from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command

ALEMBIC_CFG = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


def run_migrations() -> None:
    cfg = Config(str(ALEMBIC_CFG))
    command.upgrade(cfg, "head")
