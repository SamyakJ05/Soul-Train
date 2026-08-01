"""Small SQLite-backed store for playlist drafts awaiting Spotify publishing."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4


DRAFT_LIFETIME_SECONDS = 24 * 60 * 60


def create_draft(database_path, owner_id: str, payload: dict) -> str:
    draft_id = uuid4().hex
    now = int(time.time())
    with _connect(database_path) as connection:
        _initialize(connection)
        connection.execute(
            "DELETE FROM playlist_drafts WHERE updated_at < ?",
            (now - DRAFT_LIFETIME_SECONDS,),
        )
        connection.execute(
            """
            INSERT INTO playlist_drafts (id, owner_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (draft_id, owner_id, json.dumps(payload), now, now),
        )
    return draft_id


def get_draft(database_path, draft_id: str, owner_id: str) -> dict | None:
    with _connect(database_path) as connection:
        _initialize(connection)
        row = connection.execute(
            "SELECT payload, updated_at FROM playlist_drafts WHERE id = ? AND owner_id = ?",
            (draft_id, owner_id),
        ).fetchone()
    if not row or row["updated_at"] < int(time.time()) - DRAFT_LIFETIME_SECONDS:
        return None
    return json.loads(row["payload"])


def save_draft(database_path, draft_id: str, owner_id: str, payload: dict) -> bool:
    with _connect(database_path) as connection:
        _initialize(connection)
        cursor = connection.execute(
            """
            UPDATE playlist_drafts SET payload = ?, updated_at = ?
            WHERE id = ? AND owner_id = ?
            """,
            (json.dumps(payload), int(time.time()), draft_id, owner_id),
        )
    return cursor.rowcount == 1


def delete_draft(database_path, draft_id: str, owner_id: str) -> None:
    with _connect(database_path) as connection:
        _initialize(connection)
        connection.execute(
            "DELETE FROM playlist_drafts WHERE id = ? AND owner_id = ?",
            (draft_id, owner_id),
        )


def _connect(database_path) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def _initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS playlist_drafts (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
