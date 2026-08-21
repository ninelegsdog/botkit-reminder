from __future__ import annotations

from sqlalchemy import text

from src.core.database import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL DEFAULT 'once',
    fire_at TEXT NOT NULL,
    cron_day INTEGER,
    text TEXT NOT NULL,
    creator_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reminder_recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reminder_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    delivered_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS subscribers (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    subscribed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    segment TEXT NOT NULL DEFAULT 'all',
    sent_at TEXT,
    total INTEGER NOT NULL DEFAULT 0,
    delivered INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    unsubscribed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS broadcast_recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    broadcast_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY (broadcast_id) REFERENCES broadcasts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reminders_fire ON reminders(fire_at, is_active);
CREATE INDEX IF NOT EXISTS idx_reminder_recipients_user ON reminder_recipients(user_id);
CREATE INDEX IF NOT EXISTS idx_broadcast_recipients ON broadcast_recipients(broadcast_id, status);
"""


async def migrate(db: Database) -> None:
    async with db.transaction() as conn:
        for statement in SCHEMA.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt))
