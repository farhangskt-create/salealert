"""Optional server-side API-search budget gate. No search provider is connected here.

Call reserve_search() BEFORE every external discovery API request after integrating
an approved provider. Keep credentials ONLY on the central server. SQLite budget
is local-host-only; use a centralized backend for multi-host deployments.
"""
import sqlite3
import time
from pathlib import Path

MAX_CALLS_PER_36H = 100
MAX_CALLS_PER_UTC_DAY = 100  # Conservative safeguard, not a claim of provider free quota.
WINDOW_SECONDS = 36 * 3600

def reserve_search(db_path: str | Path, now: int | None = None) -> bool:
    """Atomically reserve one API search, or return False if budget is exhausted."""
    now = int(time.time()) if now is None else int(now)
    conn = sqlite3.connect(str(db_path), timeout=10)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS search_calls (id INTEGER PRIMARY KEY, at INTEGER NOT NULL)")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM search_calls WHERE at <= ?", (now-WINDOW_SECONDS,))
        count_window = conn.execute("SELECT COUNT(*) FROM search_calls WHERE at > ?", (now-WINDOW_SECONDS,)).fetchone()[0]
        utc_day_start = now - now % 86400
        count_today = conn.execute("SELECT COUNT(*) FROM search_calls WHERE at >= ?", (utc_day_start,)).fetchone()[0]
        if count_window >= MAX_CALLS_PER_36H or count_today >= MAX_CALLS_PER_UTC_DAY:
            conn.rollback()
            return False
        conn.execute("INSERT INTO search_calls(at) VALUES (?)", (now,))
        conn.commit()
        return True
    finally:
        conn.close()
