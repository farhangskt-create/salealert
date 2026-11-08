import os
import json
import logging
import time
from pathlib import Path
from storage.smart_scheduler_db import SmartSchedulerDB
from storage.db import ScraperDatabase
from search_budget import reserve_search
from validators.deal_validator import DealValidator
from exporters.json_pack_exporter import JsonPackExporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartScheduler")

COOLDOWN_36H_MS = 36 * 3600 * 1000

def load_backend_credentials():
    key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    if not key or not cx:
        cred_path = Path(__file__).resolve().parent / "config" / "credentials.json"
        if cred_path.exists():
            try:
                data = json.loads(cred_path.read_text(encoding="utf-8"))
                key = key or data.get("GOOGLE_CSE_API_KEY")
                cx = cx or data.get("GOOGLE_CSE_CX")
            except Exception:
                pass
    return key, cx

def run_smart_cycle():
    base_dir = Path(__file__).resolve().parent
    registry_path = base_dir / "config" / "brands_registry.json"
    db_path = base_dir / "storage" / "smart_scheduler.sqlite"
    main_db_path = base_dir / "storage" / "scraper_db.sqlite"
    output_dir = base_dir / "output"

    if not registry_path.exists():
        logger.error("Brands registry not found.")
        return 1

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    brands = registry.get("brands", [])
    scheduler_db = SmartSchedulerDB(db_path)
    scheduler_db.init_brands(brands)

    main_db = ScraperDatabase(str(main_db_path))
    validator = DealValidator()
    exporter = JsonPackExporter(str(output_dir))

    now_ms = int(time.time() * 1000)
    eligible_brands = scheduler_db.get_eligible_brands(now_ms)

    logger.info(f"Smart Scheduler: Found {len(eligible_brands)} eligible brand(s) for category rotation.")

    search_calls_made = 0
    budget_db_path = base_dir / "storage" / "search_budget.sqlite"
    api_key, cx = load_backend_credentials()

    for brand in eligible_brands:
        brand_id = brand["brandId"]
        brand_url = brand["officialUrl"]
        category = brand["category"]

        # Enforce search budget quota
        if not reserve_search(budget_db_path):
            logger.warning("Search quota exhausted (max calls reached). Stopping search cycle.")
            break

        search_calls_made += 1
        logger.info(f"Executing search rotation for [{category}] brand: {brand_url} (ID: {brand_id})")

        deals_found = []
        if api_key and cx:
            try:
                import sys
                bridge_path = Path(__file__).resolve().parent.parent / "salealert_search_bridge"
                if str(bridge_path) not in sys.path:
                    sys.path.append(str(bridge_path))
                from google_discover import search
                items = search(f"site:{brand_url} sale discount Pakistan", api_key, cx)
                for idx, item in enumerate(items):
                    link = item.get("link", "").strip()
                    title = item.get("title", "").strip()
                    snippet = item.get("snippet", "")
                    if link and title:
                        deal_id = f"{brand_id}-{idx+1}"
                        deal_record = {
                            "dealId": deal_id,
                            "merchant": brand_id,
                            "title": title,
                            "description": snippet,
                            "address": "Online",
                            "categoryId": category,
                            "cityId": "All",
                            "originalPrice": None,
                            "salePrice": None,
                            "currency": None,
                            "imageUrl": None,
                            "sourceUrl": link,
                            "latitude": None,
                            "longitude": None,
                            "startTime": now_ms,
                            "expiryTime": None,
                            "verifiedAt": None,
                            "sourceType": "brand",
                            "isSponsored": False,
                            "lastUpdated": now_ms,
                            "lastFetchedAt": now_ms,
                            "sourceHostname": "",
                            "httpStatusCode": 200,
                            "fetchedUrl": link,
                            "finalRedirectUrl": link,
                            "evidenceHash": "search_evidence",
                            "evidenceUrl": link,
                            "fetchedAt": now_ms,
                            "status": "pending",
                            "sourceId": brand_id,
                            "packId": "national"
                        }
                        is_valid, _ = validator.validate_deal(deal_record)
                        if is_valid:
                            deals_found.append(deal_record)
                            main_db.upsert_scraped_deal(deal_record)
            except Exception as e:
                logger.warning(f"Google CSE search failed for {brand_id}: {e}")
        else:
            logger.info(f"Google CSE API credentials not configured; skipping live API query for {brand_id}")

        # Update persistent search history state
        scheduler_db.update_brand_search_result(
            brand_id=brand_id,
            success=len(deals_found) > 0,
            active_deal_ids=[d["dealId"] for d in deals_found],
            deal_expiry=now_ms + (7 * 86400 * 1000),
            cooldown_duration_ms=COOLDOWN_36H_MS
        )

    # Publish approved valid deals; if zero new results, preserve existing valid database deals
    approved_deals = main_db.get_publishable_approved_deals(now_ms)

    if not approved_deals:
        logger.info("Zero new approved deals from search rotation; retaining existing valid feed packs.")
        return 0

    pack_spec = exporter.export_pack("national", 1, approved_deals)
    combined_hash = pack_spec["sha256"]
    data_version = int(combined_hash[:8], 16)
    manifest_file = exporter.generate_manifest(data_version=data_version, pack_specs=[pack_spec])

    logger.info(f"Smart Scheduler Cycle Complete. Search calls made: {search_calls_made}. Manifest: {manifest_file}")
    return 0

if __name__ == "__main__":
    raise SystemExit(run_smart_cycle())
