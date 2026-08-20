from __future__ import annotations

from alembic import command
from alembic.config import Config
from pathlib import Path


ALEMBIC_CFG = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


def run_migrations() -> None:
    cfg = Config(str(ALEMBIC_CFG))
    command.upgrade(cfg, "head")
