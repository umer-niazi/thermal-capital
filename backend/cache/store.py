"""SQLite-backed persistent local cache store for FortyGuard API responses."""

from __future__ import annotations

import datetime
import json
import pathlib
import sqlite3
from typing import Any

DEFAULT_CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "cache"
DEFAULT_DB_PATH = DEFAULT_CACHE_DIR / "api_cache.db"


class SQLiteCacheStore:
    """Persistent SQLite cache store ensuring zero redundant API calls and credit preservation."""

    def __init__(self, db_path: str | pathlib.Path | None = None) -> None:
        self.db_path = pathlib.Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed_at TEXT NOT NULL,
                    hit_count INTEGER DEFAULT 0
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_endpoint ON api_cache(endpoint);")
            conn.commit()

    def get(self, cache_key: str) -> dict[str, Any] | None:
        """Retrieve cached response JSON by cache key.

        Returns None on cache miss. On cache hit, increments hit_count and updates last_accessed_at.
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_json FROM api_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            # Update access metadata
            conn.execute(
                """
                UPDATE api_cache
                SET hit_count = hit_count + 1, last_accessed_at = ?
                WHERE cache_key = ?
                """,
                (now, cache_key),
            )
            conn.commit()

            try:
                return json.loads(row[0])
            except Exception:
                return None

    def set(
        self,
        cache_key: str,
        endpoint: str,
        payload: dict[str, Any] | None,
        response: dict[str, Any],
    ) -> None:
        """Store or update a response JSON in the cache."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload_str = json.dumps(payload or {}, sort_keys=True)
        response_str = json.dumps(response, sort_keys=True)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO api_cache (
                    cache_key, endpoint, payload_json, response_json,
                    created_at, last_accessed_at, hit_count
                )
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    last_accessed_at = excluded.last_accessed_at
                """,
                (cache_key, endpoint, payload_str, response_str, now, now),
            )
            conn.commit()

    def has(self, cache_key: str) -> bool:
        """Check if a cache key exists in the store."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM api_cache WHERE cache_key = ?", (cache_key,))
            return cursor.fetchone() is not None

    def delete(self, cache_key: str) -> bool:
        """Delete a single cache entry."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> int:
        """Clear all entries in the cache store."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM api_cache")
            conn.commit()
            return cursor.rowcount

    def stats(self) -> dict[str, Any]:
        """Return cache statistics (entry count, total hits, endpoints cached)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(hit_count) FROM api_cache")
            row = cursor.fetchone()
            count = row[0] if row else 0
            hits = row[1] if (row and row[1] is not None) else 0

            cursor.execute("SELECT endpoint, COUNT(*) FROM api_cache GROUP BY endpoint")
            breakdown = {ep: cnt for ep, cnt in cursor.fetchall()}

            return {
                "total_entries": count,
                "total_hits": hits,
                "endpoint_breakdown": breakdown,
                "db_path": str(self.db_path),
            }


_default_store: SQLiteCacheStore | None = None


def get_cache_store() -> SQLiteCacheStore:
    """Get or instantiate the global default SQLiteCacheStore."""
    global _default_store
    if _default_store is None:
        _default_store = SQLiteCacheStore()
    return _default_store
