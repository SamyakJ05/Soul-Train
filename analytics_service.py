"""Privacy-conscious, first-party usage analytics for Soul Train."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock

from database import connect


EVENT_COLUMNS = {
    "draft_created": "drafts_created",
    "playlist_published": "playlists_published",
    "stats_viewed": "stats_views",
}
_INITIALIZED_DATABASES = set()
_INITIALIZE_LOCK = Lock()


def record_visit(database_path, browser_id: str) -> None:
    now = _now()
    day = now[:10]
    with _connect(database_path) as connection:
        _initialize(connection, database_path)
        inserted = connection.execute(
            """
            INSERT INTO visitors
                (browser_id, first_seen, last_seen, page_views)
            VALUES (?, ?, ?, 0)
            ON CONFLICT (browser_id) DO NOTHING
            """,
            (browser_id, now, now),
        ).rowcount
        connection.execute(
            """
            UPDATE visitors SET last_seen = ?, page_views = page_views + 1
            WHERE browser_id = ?
            """,
            (now, browser_id),
        )
        _increment_daily(connection, day, "page_views")
        if inserted:
            _increment_daily(connection, day, "new_visitors")


def identify_visitor(
    database_path, browser_id: str, spotify_id: str | None, display_name: str | None
) -> None:
    if not spotify_id:
        return
    now = _now()
    with _connect(database_path) as connection:
        _initialize(connection, database_path)
        connection.execute(
            """
            INSERT INTO visitors
                (browser_id, first_seen, last_seen, page_views)
            VALUES (?, ?, ?, 0)
            ON CONFLICT (browser_id) DO NOTHING
            """,
            (browser_id, now, now),
        )
        connection.execute(
            """
            UPDATE visitors SET spotify_id = ?, display_name = ?, last_seen = ?
            WHERE browser_id = ?
            """,
            (spotify_id, (display_name or "Spotify listener")[:100], now, browser_id),
        )


def record_event(database_path, browser_id: str, event: str) -> None:
    column = EVENT_COLUMNS.get(event)
    if not column:
        raise ValueError("Choose a supported analytics event.")
    now = _now()
    with _connect(database_path) as connection:
        _initialize(connection, database_path)
        connection.execute(
            """
            INSERT INTO visitors
                (browser_id, first_seen, last_seen, page_views)
            VALUES (?, ?, ?, 0)
            ON CONFLICT (browser_id) DO NOTHING
            """,
            (browser_id, now, now),
        )
        connection.execute(
            f"UPDATE visitors SET {column} = {column} + 1, last_seen = ? WHERE browser_id = ?",
            (now, browser_id),
        )
        _increment_daily(connection, now[:10], column)


def analytics_summary(database_path, days: int = 14) -> dict:
    with _connect(database_path) as connection:
        _initialize(connection, database_path)
        totals = connection.execute(
            """
            SELECT
                COUNT(*) AS unique_browsers,
                COUNT(DISTINCT spotify_id) AS connected_users,
                COALESCE(SUM(page_views), 0) AS page_views,
                COALESCE(SUM(drafts_created), 0) AS drafts_created,
                COALESCE(SUM(playlists_published), 0) AS playlists_published,
                COALESCE(SUM(stats_views), 0) AS stats_views
            FROM visitors
            """
        ).fetchone()
        visitors = connection.execute(
            """
            SELECT
                spotify_id,
                COALESCE(MAX(display_name), 'Anonymous visitor') AS display_name,
                MIN(first_seen) AS first_seen,
                MAX(last_seen) AS last_seen,
                SUM(page_views) AS page_views,
                SUM(drafts_created) AS drafts_created,
                SUM(playlists_published) AS playlists_published
            FROM visitors
            GROUP BY CASE
                WHEN spotify_id IS NULL THEN 'browser:' || browser_id
                ELSE 'spotify:' || spotify_id
            END
            ORDER BY last_seen DESC
            LIMIT 50
            """
        ).fetchall()
        start_day = (datetime.now(timezone.utc) - timedelta(days=max(days - 1, 0))).date().isoformat()
        activity = connection.execute(
            """
            SELECT day, page_views, new_visitors, drafts_created,
                   playlists_published, stats_views
            FROM daily_activity WHERE day >= ? ORDER BY day
            """,
            (start_day,),
        ).fetchall()
    activity_by_day = {row["day"]: dict(row) for row in activity}
    daily = []
    for offset in range(days - 1, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()
        daily.append(activity_by_day.get(day, {
            "day": day, "page_views": 0, "new_visitors": 0,
            "drafts_created": 0, "playlists_published": 0, "stats_views": 0,
        }))
    maximum_views = max((row["page_views"] for row in daily), default=0)
    return {
        "totals": dict(totals),
        "visitors": [dict(row) for row in visitors],
        "daily": daily,
        "maximum_views": max(maximum_views, 1),
    }


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
            CREATE TABLE IF NOT EXISTS visitors (
                browser_id TEXT PRIMARY KEY,
                spotify_id TEXT,
                display_name TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                page_views INTEGER NOT NULL DEFAULT 0,
                drafts_created INTEGER NOT NULL DEFAULT 0,
                playlists_published INTEGER NOT NULL DEFAULT 0,
                stats_views INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS visitors_spotify_id ON visitors (spotify_id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_activity (
                day TEXT PRIMARY KEY,
                page_views INTEGER NOT NULL DEFAULT 0,
                new_visitors INTEGER NOT NULL DEFAULT 0,
                drafts_created INTEGER NOT NULL DEFAULT 0,
                playlists_published INTEGER NOT NULL DEFAULT 0,
                stats_views INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.commit()
        _INITIALIZED_DATABASES.add(database_key)


def _increment_daily(connection, day: str, column: str) -> None:
    connection.execute(
        """
        INSERT INTO daily_activity (day) VALUES (?)
        ON CONFLICT (day) DO NOTHING
        """,
        (day,),
    )
    connection.execute(
        f"UPDATE daily_activity SET {column} = {column} + 1 WHERE day = ?",
        (day,),
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
