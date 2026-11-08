import os
import json
import gzip
import hashlib
import time
import tempfile
import unittest
from validators.deal_validator import DealValidator
from exporters.json_pack_exporter import JsonPackExporter
from storage.db import ScraperDatabase
from parsers.generic_feed_parser import GenericFeedParser

class TestSaleAlertScraperSecurityCorrections(unittest.TestCase):

    def setUp(self):
        self.validator = DealValidator()
        self.now_ms = int(time.time() * 1000)

        # Temporary config for unit tests
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_config_path = os.path.join(self.temp_dir.name, "sources.json")
        self.test_db_path = os.path.join(self.temp_dir.name, "test.sqlite")

        config_data = {
            "sources": [
                {
                    "id": "khaadi_pk",
                    "name": "Khaadi Pakistan",
                    "type": "brand",
                    "category": "Clothes",
                    "city": "All",
                    "permission_status": "approved",
                    "authorized_hostnames": ["pk.khaadi.com", "khaadi.com"],
                    "feed_url": "https://pk.khaadi.com/"
                },
                {
                    "id": "unapproved_source",
                    "name": "Unapproved Store",
                    "type": "merchant",
                    "category": "Shopping",
                    "city": "All",
                    "permission_status": "pending_authorization",
                    "authorized_hostnames": ["unapproved.com"],
                    "feed_url": "https://unapproved.com/"
                }
            ]
        }
        with open(self.test_config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        self.sample_deal = {
            "dealId": GenericFeedParser.generate_stable_deal_id("khaadi_pk", "https://pk.khaadi.com/sale/lawn-01"),
            "merchant": "Khaadi PK",
            "title": "Authentic Lawn Sale 30% Off",
            "description": "Evidence-backed genuine brand sale",
            "address": "Nationwide Outlets",
            "categoryId": "Clothes",
            "cityId": "All",
            "originalPrice": 6000.0,
            "salePrice": 4200.0,
            "currency": "PKR",
            "imageUrl": "https://pk.khaadi.com/images/banner.jpg",
            "sourceUrl": "https://pk.khaadi.com/sale/lawn-01",
            "latitude": None,
            "longitude": None,
            "startTime": self.now_ms,
            "expiryTime": None,
            "verifiedAt": None,
            "sourceType": "brand",
            "isSponsored": False,
            "lastUpdated": self.now_ms,
            "lastFetchedAt": self.now_ms,
            "sourceHostname": "pk.khaadi.com",
            "httpStatusCode": 200,
            "fetchedUrl": "https://pk.khaadi.com/sale/lawn-01",
            "finalRedirectUrl": "https://pk.khaadi.com/sale/lawn-01",
            "evidenceHash": "sha256_evidence_hash_12345",
            "evidenceUrl": "https://pk.khaadi.com/sale/lawn-01",
            "fetchedAt": self.now_ms,
            "status": "pending",
            "sourceId": "khaadi_pk",
            "packId": "national"
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_approval_fails_for_non_200_http_status(self):
        """
        Negative Test: Prevents approving deals where HTTP status code != 200 (e.g. 404, 500, or 0).
        """
        db = ScraperDatabase(self.test_db_path, config_path=self.test_config_path)

        bad_deal = dict(self.sample_deal)
        bad_deal["dealId"] = "http-fail-01"
        bad_deal["httpStatusCode"] = 404 # Failed HTTP fetch

        db.upsert_scraped_deal(bad_deal)
        approved = db.approve_deal("http-fail-01")

        self.assertFalse(approved, "Approval must fail when httpStatusCode != 200")

    def test_approval_fails_for_unapproved_or_unknown_source(self):
        """
        Negative Test: Prevents approving deals from unknown or pending_authorization sources.
        """
        db = ScraperDatabase(self.test_db_path, config_path=self.test_config_path)

        unapproved_deal = dict(self.sample_deal)
        unapproved_deal["dealId"] = "unapproved-source-01"
        unapproved_deal["sourceId"] = "unapproved_source" # Source status is pending_authorization

        db.upsert_scraped_deal(unapproved_deal)
        approved = db.approve_deal("unapproved-source-01")

        self.assertFalse(approved, "Approval must fail for sources with permission_status != 'approved'")

    def test_approval_fails_for_forged_redirect_destination(self):
        """
        Negative Test: Prevents approving deals redirected to an unauthorized domain.
        """
        db = ScraperDatabase(self.test_db_path, config_path=self.test_config_path)

        forged_deal = dict(self.sample_deal)
        forged_deal["dealId"] = "redirect-forged-01"
        forged_deal["finalRedirectUrl"] = "https://malicious-phishing-site.com/fake"

        db.upsert_scraped_deal(forged_deal)
        approved = db.approve_deal("redirect-forged-01")

        self.assertFalse(approved, "Approval must fail if finalRedirectUrl hostname is unauthorized")

    def test_source_id_or_pack_id_change_resets_approval(self):
        """
        Negative Test: Verifies that changing sourceId or packId resets status to 'pending'.
        """
        db = ScraperDatabase(self.test_db_path, config_path=self.test_config_path)

        db.upsert_scraped_deal(self.sample_deal)
        deal_id = self.sample_deal["dealId"]
        self.assertTrue(db.approve_deal(deal_id))

        # Change sourceId
        modified = dict(self.sample_deal)
        modified["sourceId"] = "different_source"
        new_status = db.upsert_scraped_deal(modified)

        self.assertEqual(new_status, "pending", "sourceId change must reset status to 'pending'")
        self.assertEqual(len(db.get_publishable_approved_deals(self.now_ms)), 0)

    def test_export_time_re_validation_filters_revoked_sources(self):
        """
        Negative Test: Verifies that if a source is revoked in sources.json after approval,
        export-time re-validation excludes its deals from output packs.
        """
        db = ScraperDatabase(self.test_db_path, config_path=self.test_config_path)

        db.upsert_scraped_deal(self.sample_deal)
        deal_id = self.sample_deal["dealId"]
        self.assertTrue(db.approve_deal(deal_id))

        # Initially publishable
        self.assertEqual(len(db.get_publishable_approved_deals(self.now_ms)), 1)

        # Revoke source in sources.json
        revoked_config = {
            "sources": [
                {
                    "id": "khaadi_pk",
                    "name": "Khaadi Pakistan",
                    "permission_status": "disabled", # Disabled!
                    "authorized_hostnames": ["pk.khaadi.com"]
                }
            ]
        }
        with open(self.test_config_path, "w", encoding="utf-8") as f:
            json.dump(revoked_config, f)

        # Export-time re-validation MUST reject revoked source
        publishable = db.get_publishable_approved_deals(self.now_ms)
        self.assertEqual(len(publishable), 0, "Export re-validation must reject revoked sources")

    def test_deterministic_gzip_and_stable_checksum(self):
        exporter = JsonPackExporter(self.temp_dir.name)
        spec1 = exporter.export_pack("national", 1, [self.sample_deal])

        pack_file = os.path.join(self.temp_dir.name, "packs", "national.json.gz")
        with open(pack_file, "rb") as f:
            bytes1 = f.read()

        time.sleep(1)

        spec2 = exporter.export_pack("national", 1, [self.sample_deal])
        with open(pack_file, "rb") as f:
            bytes2 = f.read()

        self.assertEqual(bytes1, bytes2, "GZIP output must be 100% byte-for-byte deterministic (mtime=0)")
        self.assertEqual(spec1["sha256"], spec2["sha256"])

if __name__ == "__main__":
    unittest.main()
