import os
import json
import logging
import sys
import time
import hashlib
from parsers.generic_feed_parser import GenericFeedParser
from validators.deal_validator import DealValidator
from storage.db import ScraperDatabase
from exporters.json_pack_exporter import JsonPackExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SaleAlertScraper")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(base_dir, "config", "sources.json")
    db_file = os.path.join(base_dir, "storage", "scraper_db.sqlite")
    output_dir = os.path.join(base_dir, "output")

    logger.info("=== Starting Sale Alert Production Scraper Pipeline ===")

    if not os.path.exists(config_file):
        logger.error(f"Config file not found at {config_file}")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    sources = config_data.get("sources", [])
    parser = GenericFeedParser(timeout=10, max_retries=3, rate_limit_delay=1.0)
    validator = DealValidator()
    db = ScraperDatabase(db_file)
    exporter = JsonPackExporter(output_dir)

    now_ms = int(time.time() * 1000)
    scraped_count = 0
    rejected_count = 0

    for source in sources:
        perm_status = source.get("permission_status", "pending_authorization")
        if perm_status != "approved":
            logger.info(f"Source '{source.get('name')}' is '{perm_status}'. Skipping (Authorization required).")
            continue

        raw_deals = parser.parse(source)

        for deal in raw_deals:
            is_valid, reason = validator.validate_deal(deal)
            if is_valid:
                db.upsert_scraped_deal(deal)
                scraped_count += 1
            else:
                logger.warning(f"Rejected invalid deal: {reason}")
                rejected_count += 1

    # Fetch ONLY genuine source-verified, admin-approved deals from SQLite
    approved_deals = db.get_publishable_approved_deals(now_ms)
    pending_deals = db.get_pending_deals()

    logger.info(f"Scraping finished. Newly Scraped: {scraped_count}, Rejected: {rejected_count}")
    logger.info(f"Database Stats: {len(pending_deals)} pending review, {len(approved_deals)} publishable approved deals.")

    # Fail closed: a disconnected scraper or pending authorization must never silently
    # overwrite the existing CDN feed with an empty manifest. Expiring offers are
    # filtered independently on device and server; old CDN packs remain intact.
    if not approved_deals:
        logger.error("No currently approved, publishable offers. Keeping previously generated feed unchanged; no empty manifest will be published.")
        sys.exit(2)

    # Group approved deals by packId
    all_deals_by_pack = {}
    for deal in approved_deals:
        pack_id = deal.get("packId") or "national"
        if pack_id not in all_deals_by_pack:
            all_deals_by_pack[pack_id] = []
        all_deals_by_pack[pack_id].append(deal)

    # Ensure at least 'national' pack exists
    if "national" not in all_deals_by_pack:
        all_deals_by_pack["national"] = []

    pack_specs = []
    combined_content = ""

    for pack_id, pack_deals in all_deals_by_pack.items():
        # Sanitize deals for export
        sanitized_deals = [exporter.sanitize_deal_for_export(d) for d in pack_deals]
        sanitized_deals.sort(key=lambda d: d.get("dealId", ""))

        # Compute content hash & obtain persistent monotonic integer version
        content_hash = exporter.compute_pack_content_hash(sanitized_deals)
        pack_version = db.get_or_increment_pack_version(pack_id, content_hash)
        combined_content += f"{pack_id}:{pack_version}:{content_hash};"

        spec = exporter.export_pack(pack_id=pack_id, pack_version=pack_version, raw_deals=sanitized_deals)
        pack_specs.append(spec)

    # Manifest dataVersion derived monotonically
    manifest_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()
    manifest_data_version = db.get_or_increment_pack_version("manifest_global", manifest_hash)

    manifest_file = exporter.generate_manifest(data_version=manifest_data_version, pack_specs=pack_specs)

    logger.info("=== Sale Alert Scraper Pipeline Finished Successfully ===")
    logger.info(f"Manifest written to: {manifest_file}")

if __name__ == "__main__":
    main()
