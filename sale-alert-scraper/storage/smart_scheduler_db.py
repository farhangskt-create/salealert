import sqlite3
import os
import json
import time
import logging

logger = logging.getLogger("SmartSchedulerDB")

class SmartSchedulerDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS brand_search_history (
                    brandId TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    officialUrl TEXT NOT NULL,
                    lastSearchedTime INTEGER DEFAULT 0,
                    lastSuccessfulResultTime INTEGER DEFAULT 0,
                    activeDealIds TEXT DEFAULT '[]',
                    dealExpiry INTEGER DEFAULT 0,
                    nextEligibleSearchTime INTEGER DEFAULT 0,
                    searchStatus TEXT DEFAULT 'never_searched',
                    searchProvider TEXT DEFAULT 'google_cse'
                )
            """)
            cursor.execute("CREATE TABLE IF NOT EXISTS scheduler_state (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.commit()
        finally:
            conn.close()

    def next_category_batch(self, now_ms: int, batch_size: int = 10) -> list[dict]:
        """Persist category cursor; only eligible brands in the selected category."""
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            categories = [r[0] for r in conn.execute(
                "SELECT DISTINCT category FROM brand_search_history ORDER BY category").fetchall()]
            if not categories:
                conn.commit()
                return []
            row = conn.execute("SELECT value FROM scheduler_state WHERE name='last_category'").fetchone()
            start = (categories.index(row[0]) + 1) % len(categories) if row and row[0] in categories else 0
            selected = []
            chosen = None
            for offset in range(len(categories)):
                category = categories[(start + offset) % len(categories)]
                rows = conn.execute("""
                    SELECT * FROM brand_search_history WHERE category = ?
                    AND (searchStatus = 'never_searched' OR nextEligibleSearchTime <= ?)
                    ORDER BY nextEligibleSearchTime, lastSearchedTime, brandId LIMIT ?
                """, (category, now_ms, batch_size)).fetchall()
                if rows:
                    selected = [dict(r) for r in rows]
                    chosen = category
                    break
            if chosen is not None:
                conn.execute("INSERT INTO scheduler_state(name,value) VALUES('last_category',?) "
                             "ON CONFLICT(name) DO UPDATE SET value=excluded.value", (chosen,))
            conn.commit()
            return selected
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_search_attempt(self, brand_id: str, found_leads: bool, cooldown_duration_ms: int):
        """Record a genuine completed provider request without destroying active deals."""
        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE brand_search_history SET
                    lastSearchedTime = ?,
                    lastSuccessfulResultTime = CASE WHEN ? THEN ? ELSE lastSuccessfulResultTime END,
                    nextEligibleSearchTime = CASE
                        WHEN dealExpiry > ? AND activeDealIds != '[]' THEN dealExpiry
                        ELSE ? END,
                    searchStatus = CASE
                        WHEN dealExpiry > ? AND activeDealIds != '[]' THEN 'active_sale'
                        ELSE 'cooldown' END
                WHERE brandId = ?
            """, (now_ms, int(found_leads), now_ms, now_ms, now_ms + cooldown_duration_ms, now_ms, brand_id))
            conn.commit()
        finally:
            conn.close()

    def init_brands(self, brands: list[dict]):
        now = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            for b in brands:
                cursor.execute("""
                    INSERT INTO brand_search_history (brandId, category, officialUrl, nextEligibleSearchTime, searchStatus)
                    VALUES (?, ?, ?, ?, 'never_searched')
                    ON CONFLICT(brandId) DO UPDATE SET
                        category = excluded.category,
                        officialUrl = excluded.officialUrl
                """, (b["id"], b["category"], b["officialUrl"], 0))
            conn.commit()
        finally:
            conn.close()

    def get_eligible_brands(self, now_ms: int = None) -> list[dict]:
        if now_ms is None:
            now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            # Prioritize: never_searched first, then expired_sale or cooldown ended (nextEligibleSearchTime <= now)
            cursor.execute("""
                SELECT * FROM brand_search_history
                WHERE searchStatus = 'never_searched'
                   OR nextEligibleSearchTime <= ?
                ORDER BY
                    CASE searchStatus
                        WHEN 'never_searched' THEN 1
                        WHEN 'expired_sale' THEN 2
                        WHEN 'cooldown' THEN 3
                        ELSE 4
                    END,
                    nextEligibleSearchTime ASC
            """, (now_ms,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_brand_search_result(self, brand_id: str, success: bool, active_deal_ids: list[str], deal_expiry: int, cooldown_duration_ms: int):
        now_ms = int(time.time() * 1000)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            if success and active_deal_ids:
                status = "active_sale"
                next_eligible = deal_expiry if deal_expiry > now_ms else now_ms + cooldown_duration_ms
                last_success = now_ms
            else:
                # Never clear existing verified active sales on empty/failed discovery.
                cursor.execute("SELECT activeDealIds, dealExpiry FROM brand_search_history WHERE brandId=?", (brand_id,))
                previous = cursor.fetchone()
                if previous and previous["dealExpiry"] > now_ms and previous["activeDealIds"] != '[]':
                    status = "active_sale"
                    next_eligible = previous["dealExpiry"]
                    active_deal_ids = json.loads(previous["activeDealIds"])
                    deal_expiry = previous["dealExpiry"]
                else:
                    status = "cooldown"
                    next_eligible = now_ms + cooldown_duration_ms
                    active_deal_ids = []
                    deal_expiry = 0
                last_success = 0

            cursor.execute("""
                UPDATE brand_search_history SET
                    lastSearchedTime = ?,
                    lastSuccessfulResultTime = CASE WHEN ? = 1 THEN ? else lastSuccessfulResultTime END,
                    activeDealIds = ?,
                    dealExpiry = ?,
                    nextEligibleSearchTime = ?,
                    searchStatus = ?
                WHERE brandId = ?
            """, (now_ms, 1 if success else 0, now_ms, json.dumps(active_deal_ids), deal_expiry, next_eligible, status, brand_id))
            conn.commit()
        finally:
            conn.close()
