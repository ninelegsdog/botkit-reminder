from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.core.database import Database


async def subscribe(db: Database, user_id: int, username: str | None = None, name: str | None = None) -> None:
    async with db.transaction() as session:
        await session.execute(
            text(
                "INSERT OR REPLACE INTO subscribers (user_id, username, name, is_active, subscribed_at) "
                "VALUES (:uid, :uname, :name, 1, datetime('now'))"
            ),
            {"uid": user_id, "uname": username, "name": name},
        )


async def unsubscribe(db: Database, user_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text("UPDATE subscribers SET is_active = 0 WHERE user_id = :uid"),
            {"uid": user_id},
        )


async def get_active_subscribers(db: Database) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(
            text("SELECT * FROM subscribers WHERE is_active = 1")
        )
        return [dict(r) for r in result.mappings().all()]


async def create_reminder(
    db: Database,
    *,
    creator_id: int,
    reminder_type: str,
    fire_at: str,
    text_content: str,
    cron_day: int | None = None,
) -> int:
    async with db.transaction() as session:
        result = await session.execute(
            text(
                "INSERT INTO reminders (type, fire_at, cron_day, text, creator_id) "
                "VALUES (:type, :fire_at, :cron_day, :text, :creator_id)"
            ),
            {
                "type": reminder_type,
                "fire_at": fire_at,
                "cron_day": cron_day,
                "text": text_content,
                "creator_id": creator_id,
            },
        )
        rem_id = result.lastrowid  # type: ignore[attr-defined]
        assert rem_id is not None
        return int(rem_id)


async def get_user_reminders(db: Database, user_id: int) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT * FROM reminders WHERE creator_id = :uid AND is_active = 1"
            ),
            {"uid": user_id},
        )
        return [dict(r) for r in result.mappings().all()]


async def cancel_reminder(db: Database, reminder_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text("UPDATE reminders SET is_active = 0 WHERE id = :rid"),
            {"rid": reminder_id},
        )


async def get_due_reminders(db: Database) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT * FROM reminders WHERE fire_at <= datetime('now') AND is_active = 1"
            )
        )
        return [dict(r) for r in result.mappings().all()]


async def mark_reminder_done(db: Database, reminder_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text("UPDATE reminders SET is_active = 0 WHERE id = :rid"),
            {"rid": reminder_id},
        )


async def add_reminder_recipient(db: Database, reminder_id: int, user_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO reminder_recipients (reminder_id, user_id) VALUES (:rid, :uid)"
            ),
            {"rid": reminder_id, "uid": user_id},
        )


async def mark_recipient_delivered(db: Database, reminder_id: int, user_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text(
                "UPDATE reminder_recipients SET status = 'delivered', delivered_at = datetime('now') "
                "WHERE reminder_id = :rid AND user_id = :uid"
            ),
            {"rid": reminder_id, "uid": user_id},
        )


async def create_broadcast(db: Database, *, text_content: str, segment: str) -> int:
    async with db.transaction() as session:
        result = await session.execute(
            text(
                "INSERT INTO broadcasts (text, segment) VALUES (:text, :seg)"
            ),
            {"text": text_content, "seg": segment},
        )
        bc_id = result.lastrowid  # type: ignore[attr-defined]
        assert bc_id is not None
        return int(bc_id)


async def add_broadcast_recipient(db: Database, broadcast_id: int, user_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text(
                "INSERT INTO broadcast_recipients (broadcast_id, user_id) VALUES (:bid, :uid)"
            ),
            {"bid": broadcast_id, "uid": user_id},
        )


async def mark_broadcast_delivered(db: Database, broadcast_id: int, user_id: int) -> None:
    async with db.transaction() as session:
        await session.execute(
            text(
                "UPDATE broadcast_recipients SET status = 'delivered' "
                "WHERE broadcast_id = :bid AND user_id = :uid"
            ),
            {"bid": broadcast_id, "uid": user_id},
        )


async def get_broadcast_stats(db: Database, broadcast_id: int) -> dict[str, int]:
    async with db.session() as session:
        result = await session.execute(
            text(
                "SELECT status, COUNT(*) as cnt FROM broadcast_recipients "
                "WHERE broadcast_id = :bid GROUP BY status"
            ),
            {"bid": broadcast_id},
        )
        rows = result.mappings().all()
        return {r["status"]: r["cnt"] for r in rows}


async def get_broadcasts(db: Database) -> list[dict[str, Any]]:
    async with db.session() as session:
        result = await session.execute(
            text("SELECT * FROM broadcasts ORDER BY sent_at DESC LIMIT 10")
        )
        return [dict(r) for r in result.mappings().all()]
