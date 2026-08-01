"""Database connection compatibility for local SQLite and hosted PostgreSQL."""

from __future__ import annotations

from pathlib import Path


POSTGRES_SCHEMES = ("postgres://", "postgresql://")


def is_postgres(database_target) -> bool:
    return str(database_target).lower().startswith(POSTGRES_SCHEMES)


def connect(database_target):
    """Return a small DB-API adapter with mapping-style result rows."""
    return DatabaseConnection(database_target)


class DatabaseConnection:
    def __init__(self, database_target):
        self._postgres = is_postgres(database_target)
        if self._postgres:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as exc:  # pragma: no cover - deployment guard
                raise RuntimeError(
                    "PostgreSQL requires the psycopg package from requirements.txt."
                ) from exc
            self._connection = psycopg.connect(
                str(database_target), row_factory=dict_row
            )
        else:
            import sqlite3

            path = Path(database_target)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(path, timeout=5)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")

    def execute(self, query: str, parameters=()):
        if self._postgres:
            query = _postgres_placeholders(query)
        return self._connection.execute(query, parameters)

    def commit(self):
        self._connection.commit()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            if exception_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()
        return False


def _postgres_placeholders(query: str) -> str:
    """Convert the project's DB-API qmark placeholders for psycopg."""
    return query.replace("?", "%s")
