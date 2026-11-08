import json
import logging
import time
import hashlib
import re
from urllib.parse import urlparse
from .base_parser import BaseParser

logger = logging.getLogger("GenericFeedParser")

class GenericFeedParser(BaseParser):
    @staticmethod
    def generate_stable_deal_id(source_id: str, canonical_url: str) -> str:
        clean_url = canonical_url.strip().lower()
        url_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]
        return f"{source_id}-{url_hash}"

    @staticmethod
    def compute_deal_evidence_hash(title: str, original_price: float, sale_price: float, source_url: str, final_url: str) -> str:
        raw_str = f"{title}:{original_price}:{sale_price}:{source_url}:{final_url}"
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    def parse(self, source_config: dict) -> list[dict]:
        source_id = source_config.get("id", "unknown")
        source_name = source_config.get("name", "Unknown Source")
        perm_status = source_config.get("permission_status", "pending_authorization")
        feed_url = source_config.get("feed_url", "")
        auth_hostnames = [h.lower() for h in source_config.get("authorized_hostnames", [])]

        if perm_status != "approved":
            logger.info(f"Skipping source '{source_name}' ({source_id}): Permission status is '{perm_status}'.")
            return []

        if not feed_url:
            logger.warning(f"Source '{source_name}' has no feed_url configured.")
            return []

        raw_content, final_redirect_url, http_status_code = self.fetch_url_with_details(feed_url)

        # No fabricated HTTP defaults!
        if http_status_code != 200 or not raw_content:
            logger.warning(f"Fetch failed for source '{source_name}' (HTTP {http_status_code}). Returning empty list.")
            return []

        deals = []
        now_ms = int(time.time() * 1000)

        try:
            if raw_content.strip().startswith("{") or raw_content.strip().startswith("["):
                json_data = json.loads(raw_content)
                deals = self._extract_from_json(json_data, source_config, now_ms, auth_hostnames, feed_url, final_redirect_url, http_status_code)
            else:
                deals = self._extract_from_html(raw_content, source_config, now_ms, auth_hostnames, feed_url, final_redirect_url, http_status_code)
        except Exception as e:
            logger.error(f"Error parsing content from {source_name}: {e}")
            return []

        logger.info(f"Source '{source_name}' returned {len(deals)} valid candidate deal(s).")
        return deals

    def _extract_from_json(self, data: dict | list, config: dict, now_ms: int, auth_hostnames: list[str], fetched_url: str, final_redirect_url: str, http_code: int) -> list[dict]:
        results = []
        items = data if isinstance(data, list) else data.get("slides") or data.get("items") or []

        for item in items:
            if isinstance(item, dict):
                title = item.get("title") or item.get("name") or item.get("heading")
                url = item.get("url") or item.get("link")
                orig_price = item.get("originalPrice") or item.get("price")
                sale_price = item.get("salePrice") or item.get("discountPrice")

                if title and url:
                    canonical_url = str(url).strip()
                    parsed = urlparse(canonical_url)
                    hostname = (parsed.hostname or "").lower()

                    # Exact Hostname Check for canonical url
                    if auth_hostnames and hostname not in auth_hostnames:
                        logger.warning(f"Forged/unauthorized hostname '{hostname}' rejected for source '{config['id']}'")
                        continue

                    deal_id = self.generate_stable_deal_id(config["id"], canonical_url)
                    op = float(orig_price) if orig_price is not None else None
                    sp = float(sale_price) if sale_price is not None else None
                    ev_hash = self.compute_deal_evidence_hash(str(title).strip(), op, sp, canonical_url, final_redirect_url)

                    results.append({
                        "dealId": deal_id,
                        "merchant": config.get("name"),
                        "title": str(title).strip(),
                        "description": item.get("description"),
                        "address": config.get("address"),
                        "categoryId": config.get("category", "Shopping"),
                        "cityId": config.get("city", "All"),
                        "originalPrice": op,
                        "salePrice": sp,
                        "currency": "PKR" if op is not None else None,
                        "imageUrl": item.get("imageUrl") or item.get("image"),
                        "sourceUrl": canonical_url,
                        "latitude": None,
                        "longitude": None,
                        "startTime": item.get("startTime"),
                        "expiryTime": item.get("expiryTime"),
                        "verifiedAt": None,
                        "sourceType": config.get("type", "brand"),
                        "isSponsored": False,
                        "lastUpdated": now_ms,
                        "lastFetchedAt": now_ms,
                        "sourceHostname": hostname,
                        "httpStatusCode": http_code,
                        "fetchedUrl": fetched_url,
                        "finalRedirectUrl": final_redirect_url,
                        "evidenceHash": ev_hash,
                        "evidenceUrl": canonical_url,
                        "fetchedAt": now_ms,
                        "status": "pending",
                        "sourceId": config["id"],
                        "packId": "national" if config.get("city", "All") == "All" else config.get("city").lower()
                    })

        return results

    def _extract_from_html(self, html_text: str, config: dict, now_ms: int, auth_hostnames: list[str], fetched_url: str, final_redirect_url: str, http_code: int) -> list[dict]:
        results = []
        pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
        matches = pattern.findall(html_text)

        for href, text in matches:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if any(k in clean_text.lower() for k in ["sale", "discount", "off", "deal"]):
                full_url = href if href.startswith("http") else config["feed_url"].rstrip("/") + "/" + href.lstrip("/")
                parsed = urlparse(full_url)
                hostname = (parsed.hostname or "").lower()

                if auth_hostnames and hostname not in auth_hostnames:
                    logger.warning(f"Forged/unauthorized hostname '{hostname}' rejected for source '{config['id']}'")
                    continue

                deal_id = self.generate_stable_deal_id(config["id"], full_url)
                ev_hash = self.compute_deal_evidence_hash(clean_text[:100], None, None, full_url, final_redirect_url)

                results.append({
                    "dealId": deal_id,
                    "merchant": config.get("name"),
                    "title": clean_text[:100],
                    "description": clean_text,
                    "address": None,
                    "categoryId": config.get("category", "Shopping"),
                    "cityId": config.get("city", "All"),
                    "originalPrice": None,
                    "salePrice": None,
                    "currency": None,
                    "imageUrl": None,
                    "sourceUrl": full_url,
                    "latitude": None,
                    "longitude": None,
                    "startTime": None,
                    "expiryTime": None,
                    "verifiedAt": None,
                    "sourceType": config.get("type", "brand"),
                    "isSponsored": False,
                    "lastUpdated": now_ms,
                    "lastFetchedAt": now_ms,
                    "sourceHostname": hostname,
                    "httpStatusCode": http_code,
                    "fetchedUrl": fetched_url,
                    "finalRedirectUrl": final_redirect_url,
                    "evidenceHash": ev_hash,
                    "evidenceUrl": full_url,
                    "fetchedAt": now_ms,
                    "status": "pending",
                    "sourceId": config["id"],
                    "packId": "national" if config.get("city", "All") == "All" else config.get("city").lower()
                })

        return results
