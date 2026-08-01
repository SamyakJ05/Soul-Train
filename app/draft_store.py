"""Small SQLite-backed store for playlist drafts awaiting Spotify publishing."""

from __future__ import annotations

import json
import time
from threading import Lock
from uuid import uuid4

from .database import connect


DRAFT_LIFETIME_SECONDS = 24 * 60 * 60
_INITIALIZED_DATABASES = set()
_INITIALIZE_LOCK = Lock()


def create_draft(database_path, owner_id: str, payload: dict) -> str:
    draft_id = uuid4().hex
    now = int(time.time())
    with _connect(database_path) as connection:
        _initialize(connection, database_path)
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
        _initialize(connection, database_path)
        row = connection.execute(
            "SELECT payload, updated_at FROM playlist_drafts WHERE id = ? AND owner_id = ?",
            (draft_id, owner_id),
        ).fetchone()
    if not row or row["updated_at"] < int(time.time()) - DRAFT_LIFETIME_SECONDS:
        return None
    return json.loads(row["payload"])


def save_draft(database_path, draft_id: str, owner_id: str, payload: dict) -> bool:
    with _connect(database_path) as connection:
        _initialize(connection, database_path)
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
        _initialize(connection, database_path)
        connection.execute(
            "DELETE FROM playlist_drafts WHERE id = ? AND owner_id = ?",
            (draft_id, owner_id),
        )


def _connect(database_path):
    return connect(database_path)


def _initialize(connection, database_path) -> None:
    database_key = str(database_path)
    if database_key in _INITIALIZED_DATABASES:
        return
    with _INITIALIZE_LOCK:
        if database_key in _INITIALIZED_DATABASES:
            return
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
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS playlist_drafts_owner_id
            ON playlist_drafts (owner_id)
            """
        )
        connection.commit()
        _INITIALIZED_DATABASES.add(database_key)
