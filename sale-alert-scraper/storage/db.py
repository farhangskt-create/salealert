import sqlite3
import os
import json
import time
import logging
import hashlib
from urllib.parse import urlparse

logger = logging.getLogger("ScraperDatabase")

MATERIAL_PUBLIC_FIELDS = [
    "title", "description", "originalPrice", "salePrice", "currency",
    "sourceUrl", "imageUrl", "merchant", "categoryId", "cityId",
    "address", "latitude", "longitude", "startTime", "expiryTime",
    "isSponsored", "sourceType", "sourceId", "packId"
]

class ScraperDatabase:
    def __init__(self, db_path: str, config_path: str = None):
        self.db_path = db_path
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "sources.json")
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
                CREATE TABLE IF NOT EXISTS deals_store (
                    dealId TEXT PRIMARY KEY,
                    merchant TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    address TEXT,
                    categoryId TEXT NOT NULL,
                    cityId TEXT,
                    originalPrice REAL,
                    salePrice REAL,
                    currency TEXT,
                    imageUrl TEXT,
                    sourceUrl TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    startTime INTEGER,
                    expiryTime INTEGER,
                    verifiedAt INTEGER,
                    sourceType TEXT NOT NULL,
                    isSponsored INTEGER DEFAULT 0,
                    lastUpdated INTEGER NOT NULL,
                    lastFetchedAt INTEGER NOT NULL,
                    sourceHostname TEXT NOT NULL DEFAULT '',
                    httpStatusCode INTEGER NOT NULL DEFAULT 0,
                    fetchedUrl TEXT NOT NULL DEFAULT '',
                    finalRedirectUrl TEXT NOT NULL DEFAULT '',
                    evidenceHash TEXT NOT NULL DEFAULT '',
                    evidenceUrl TEXT NOT NULL DEFAULT '',
                    fetchedAt INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    sourceId TEXT NOT NULL,
                    packId TEXT NOT NULL
                )
            """)

            cursor.execute("PRAGMA table_info(deals_store)")
            existing_cols = [row["name"] for row in cursor.fetchall()]

            if "fetchedUrl" not in existing_cols:
                cursor.execute("ALTER TABLE deals_store ADD COLUMN fetchedUrl TEXT NOT NULL DEFAULT ''")
            if "finalRedirectUrl" not in existing_cols:
                cursor.execute("ALTER TABLE deals_store ADD COLUMN finalRedirectUrl TEXT NOT NULL DEFAULT ''")
            if "evidenceHash" not in existing_cols:
                cursor.execute("ALTER TABLE deals_store ADD COLUMN evidenceHash TEXT NOT NULL DEFAULT ''")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_versions (
                    packId TEXT PRIMARY KEY,
                    version INTEGER NOT NULL DEFAULT 1,
                    contentHash TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON deals_store(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expiry ON deals_store(expiryTime);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_packId ON deals_store(packId);")
            conn.commit()
        finally:
            conn.close()

    def load_sources_config(self) -> dict:
        if not os.path.exists(self.config_path):
            logger.warning(f"Sources config not found at {self.config_path}")
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {s["id"]: s for s in data.get("sources", [])}
        except Exception as e:
            logger.error(f"Failed to load sources config: {e}")
            return {}

    @staticmethod
    def compute_deal_evidence_hash(deal: dict) -> str:
        """
        Computes SHA-256 evidence hash connecting deal title, prices, source URL, and final redirect URL.
        """
        raw_str = f"{deal.get('title')}:{deal.get('originalPrice')}:{deal.get('salePrice')}:{deal.get('sourceUrl')}:{deal.get('finalRedirectUrl')}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def upsert_scraped_deal(self, deal: dict) -> str:
        """
        Upserts a scraped candidate deal.
        If ANY public-facing material field, sourceId, or packId changes, resets status to 'pending'!
        """
        now_ms = int(time.time() * 1000)
        deal_id = deal["dealId"]
        source_url = deal["sourceUrl"]
        final_redirect_url = deal.get("finalRedirectUrl") or source_url
        parsed_uri = urlparse(final_redirect_url)
        source_hostname = (parsed_uri.hostname or "").lower()
        http_code = deal.get("httpStatusCode", 0)
        evidence_hash = self.compute_deal_evidence_hash(deal)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deals_store WHERE dealId = ?", (deal_id,))
            row = cursor.fetchone()

            if row:
                existing_status = row["status"]
                existing_verified = row["verifiedAt"]

                # Material change detection including sourceId and packId
                material_changed = False
                for field in MATERIAL_PUBLIC_FIELDS:
                    if row[field] != deal.get(field):
                        material_changed = True
                        break

                if material_changed:
                    logger.info(f"Material change detected for deal '{deal_id}'. Resetting status to 'pending'.")
                    new_status = "pending"
                    new_verified = None
                else:
                    new_status = existing_status
                    new_verified = existing_verified

                cursor.execute("""
                    UPDATE deals_store SET
                        merchant = ?, title = ?, description = ?, address = ?,
                        categoryId = ?, cityId = ?, originalPrice = ?, salePrice = ?,
                        currency = ?, imageUrl = ?, sourceUrl = ?, latitude = ?,
                        longitude = ?, startTime = ?, expiryTime = ?, verifiedAt = ?,
                        sourceType = ?, isSponsored = ?, lastUpdated = ?, lastFetchedAt = ?,
                        sourceHostname = ?, httpStatusCode = ?, fetchedUrl = ?, finalRedirectUrl = ?,
                        evidenceHash = ?, evidenceUrl = ?, fetchedAt = ?,
                        status = ?, sourceId = ?, packId = ?
                    WHERE dealId = ?
                """, (
                    deal["merchant"], deal["title"], deal.get("description"), deal.get("address"),
                    deal["categoryId"], deal.get("cityId", "All"), deal.get("originalPrice"), deal.get("salePrice"),
                    deal.get("currency"), deal.get("imageUrl"), source_url, deal.get("latitude"),
                    deal.get("longitude"), deal.get("startTime"), deal.get("expiryTime"), new_verified,
                    deal.get("sourceType", "brand"), 1 if deal.get("isSponsored") else 0, deal.get("lastUpdated", now_ms),
                    now_ms, source_hostname, http_code, deal.get("fetchedUrl", source_url), final_redirect_url,
                    evidence_hash, deal.get("evidenceUrl", source_url), now_ms, new_status,
                    deal.get("sourceId", "unknown"), deal.get("packId", "national"), deal_id
                ))
                conn.commit()
                return new_status
            else:
                cursor.execute("""
                    INSERT INTO deals_store (
                        dealId, merchant, title, description, address, categoryId, cityId,
                        originalPrice, salePrice, currency, imageUrl, sourceUrl, latitude, longitude,
                        startTime, expiryTime, verifiedAt, sourceType, isSponsored, lastUpdated,
                        lastFetchedAt, sourceHostname, httpStatusCode, fetchedUrl, finalRedirectUrl,
                        evidenceHash, evidenceUrl, fetchedAt, status, sourceId, packId
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """, (
                    deal_id, deal["merchant"], deal["title"], deal.get("description"), deal.get("address"),
                    deal["categoryId"], deal.get("cityId", "All"), deal.get("originalPrice"), deal.get("salePrice"),
                    deal.get("currency"), deal.get("imageUrl"), source_url, deal.get("latitude"),
                    deal.get("longitude"), deal.get("startTime"), deal.get("expiryTime"), None,
                    deal.get("sourceType", "brand"), 1 if deal.get("isSponsored") else 0, deal.get("lastUpdated", now_ms),
                    now_ms, source_hostname, http_code, deal.get("fetchedUrl", source_url), final_redirect_url,
                    evidence_hash, deal.get("evidenceUrl", source_url), now_ms,
                    deal.get("sourceId", "unknown"), deal.get("packId", "national")
                ))
                conn.commit()
                return "pending"
        finally:
            conn.close()

    def approve_deal(self, deal_id: str) -> bool:
        """
        MANDATORY: Validates real source evidence internally against config/sources.json:
        - sourceId exists in sources.json and has permission_status == 'approved'
        - authorized_hostnames is non-empty
        - sourceUrl and finalRedirectUrl hostnames match authorized_hostnames
        - httpStatusCode == 200 (No fabricated defaults!)
        - evidenceHash is present
        - sourceUrl starts with 'https://' and is not example.com
        """
        now_ms = int(time.time() * 1000)
        sources_map = self.load_sources_config()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sourceId, sourceUrl, finalRedirectUrl, sourceHostname, httpStatusCode, evidenceHash
                FROM deals_store WHERE dealId = ?
            """, (deal_id,))
            row = cursor.fetchone()

            if not row:
                logger.error(f"Cannot approve deal '{deal_id}': Record not found in database.")
                return False

            source_id = row["sourceId"]
            source_url = row["sourceUrl"] or ""
            final_redirect_url = row["finalRedirectUrl"] or source_url
            http_code = row["httpStatusCode"]
            evidence_hash = row["evidenceHash"] or ""

            # 1. Source Registry Validation
            if source_id not in sources_map:
                logger.error(f"Approval rejected for deal '{deal_id}': Unknown sourceId '{source_id}'.")
                return False

            source_config = sources_map[source_id]
            if source_config.get("permission_status") != "approved":
                logger.error(f"Approval rejected for deal '{deal_id}': Source '{source_id}' permission_status is not 'approved'.")
                return False

            auth_hostnames = [h.lower() for h in source_config.get("authorized_hostnames", [])]
            if not auth_hostnames:
                logger.error(f"Approval rejected for deal '{deal_id}': Source '{source_id}' has empty authorized_hostnames list.")
                return False

            # 2. Hostname Match Check for sourceUrl and finalRedirectUrl
            url_hostname = (urlparse(source_url).hostname or "").lower()
            redirect_hostname = (urlparse(final_redirect_url).hostname or "").lower()

            if url_hostname not in auth_hostnames or redirect_hostname not in auth_hostnames:
                logger.error(f"Approval rejected for deal '{deal_id}': Hostname '{url_hostname}'/'{redirect_hostname}' is not authorized.")
                return False

            # 3. HTTP Evidence Validation
            if http_code != 200:
                logger.error(f"Approval rejected for deal '{deal_id}': HTTP status code is {http_code} (Must be 200 OK).")
                return False

            if not evidence_hash:
                logger.error(f"Approval rejected for deal '{deal_id}': Missing evidenceHash.")
                return False

            if not source_url.startswith("https://") or "example.com" in source_url:
                logger.error(f"Approval rejected for deal '{deal_id}': Invalid or test source URL '{source_url}'.")
                return False

            cursor.execute("""
                UPDATE deals_store
                SET status = 'approved', verifiedAt = ?
                WHERE dealId = ?
            """, (now_ms, deal_id))
            conn.commit()
            logger.info(f"Admin approved deal '{deal_id}' with verified source evidence.")
            return cursor.rowcount > 0
        finally:
            conn.close()

    def reject_deal(self, deal_id: str) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE deals_store SET status = 'rejected' WHERE dealId = ?", (deal_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_pending_deals(self) -> list[dict]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM deals_store WHERE status = 'pending'")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_publishable_approved_deals(self, now_ms: int = None) -> list[dict]:
        """
        Export-time re-validation:
        Enforces that every approved deal's sourceId remains approved in sources.json,
        httpStatusCode == 200, sourceHostname matches authorized_hostnames, and not expired.
        """
        if now_ms is None:
            now_ms = int(time.time() * 1000)

        sources_map = self.load_sources_config()

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM deals_store
                WHERE status = 'approved'
                  AND verifiedAt IS NOT NULL
                  AND httpStatusCode = 200
                  AND sourceUrl IS NOT NULL
                  AND sourceUrl LIKE 'https://%'
                  AND sourceUrl NOT LIKE '%example.com%'
                  AND (expiryTime IS NULL OR expiryTime > ?)
            """, (now_ms,))
            rows = cursor.fetchall()
            result = []

            for row in rows:
                d = dict(row)
                source_id = d["sourceId"]
                source_url = d["sourceUrl"]
                final_redirect_url = d.get("finalRedirectUrl") or source_url

                # Export-time Re-Validation against config/sources.json
                if source_id not in sources_map:
                    logger.warning(f"Export re-validation skipped deal '{d['dealId']}': Source '{source_id}' not in registry.")
                    continue

                source_cfg = sources_map[source_id]
                if source_cfg.get("permission_status") != "approved":
                    logger.warning(f"Export re-validation skipped deal '{d['dealId']}': Source '{source_id}' permission is no longer approved.")
                    continue

                auth_hostnames = [h.lower() for h in source_cfg.get("authorized_hostnames", [])]
                url_hostname = (urlparse(source_url).hostname or "").lower()
                redirect_hostname = (urlparse(final_redirect_url).hostname or "").lower()

                if not auth_hostnames or url_hostname not in auth_hostnames or redirect_hostname not in auth_hostnames:
                    logger.warning(f"Export re-validation skipped deal '{d['dealId']}': Hostname '{url_hostname}'/'{redirect_hostname}' is not authorized.")
                    continue

                d["isSponsored"] = bool(d["isSponsored"])
                d["status"] = "active"
                result.append(d)

            return result
        finally:
            conn.close()

    def get_or_increment_pack_version(self, pack_id: str, content_hash: str) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT version, contentHash FROM pack_versions WHERE packId = ?", (pack_id,))
            row = cursor.fetchone()

            if row:
                stored_version = row["version"]
                stored_hash = row["contentHash"]
                if stored_hash == content_hash:
                    return stored_version
                else:
                    new_version = stored_version + 1
                    cursor.execute("""
                        UPDATE pack_versions SET version = ?, contentHash = ? WHERE packId = ?
                    """, (new_version, content_hash, pack_id))
                    conn.commit()
                    return new_version
            else:
                initial_version = 1
                cursor.execute("""
                    INSERT INTO pack_versions (packId, version, contentHash) VALUES (?, ?, ?)
                """, (pack_id, initial_version, content_hash))
                conn.commit()
                return initial_version
        finally:
            conn.close()
