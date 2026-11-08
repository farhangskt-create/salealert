import json
import gzip
import hashlib
import os
import io
import logging
from datetime import datetime, timezone

logger = logging.getLogger("JsonPackExporter")

PUBLIC_DEAL_KEYS = [
    "dealId", "merchant", "title", "description", "address",
    "categoryId", "cityId", "originalPrice", "salePrice", "currency",
    "imageUrl", "sourceUrl", "latitude", "longitude",
    "startTime", "expiryTime", "verifiedAt", "sourceType",
    "isSponsored", "lastUpdated", "status"
]

class JsonPackExporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.packs_dir = os.path.join(output_dir, "packs")
        os.makedirs(self.packs_dir, exist_ok=True)

    @staticmethod
    def sanitize_deal_for_export(deal: dict) -> dict:
        """
        Extracts public fields matching Android DealEntity schema.
        Strips internal tracking metadata.
        """
        public_deal = {}
        for key in PUBLIC_DEAL_KEYS:
            public_deal[key] = deal.get(key)
        return public_deal

    @staticmethod
    def compute_pack_content_hash(public_deals: list[dict]) -> str:
        """
        Computes deterministic SHA-256 hash of public deals list sorted by dealId.
        """
        sorted_deals = sorted(public_deals, key=lambda d: d.get("dealId", ""))
        content_bytes = json.dumps(sorted_deals, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()

    @staticmethod
    def gzip_compress_deterministic(data_bytes: bytes) -> bytes:
        """
        Compresses bytes using GZIP with mtime=0 to ensure byte-for-byte deterministic output.
        """
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
            gz.write(data_bytes)
        return buf.getvalue()

    def export_pack(self, pack_id: str, pack_version: int, raw_deals: list[dict]) -> dict:
        """
        Exports a public deal pack as a deterministic gzipped JSON file (.json.gz).
        """
        public_deals = [self.sanitize_deal_for_export(d) for d in raw_deals]
        public_deals.sort(key=lambda d: d.get("dealId", ""))

        pack_filename = f"{pack_id}.json.gz"
        pack_file_path = os.path.join(self.packs_dir, pack_filename)

        pack_data = {
            "schemaVersion": 1,
            "deals": public_deals
        }

        json_bytes = json.dumps(pack_data, indent=2, ensure_ascii=False).encode("utf-8")
        compressed_bytes = self.gzip_compress_deterministic(json_bytes)

        with open(pack_file_path, "wb") as f:
            f.write(compressed_bytes)

        sha256_checksum = hashlib.sha256(compressed_bytes).hexdigest().lower()
        file_size_bytes = len(compressed_bytes)

        relative_url = f"packs/{pack_filename}"

        logger.info(f"Exported pack '{pack_id}' (version={pack_version}, count={len(public_deals)}): {file_size_bytes} bytes, SHA-256={sha256_checksum}")

        return {
            "id": pack_id,
            "version": pack_version,
            "url": relative_url,
            "sha256": sha256_checksum,
            "sizeBytes": file_size_bytes
        }

    def generate_manifest(self, data_version: int, pack_specs: list[dict]) -> str:
        """
        Generates and writes manifest.json.
        """
        manifest_path = os.path.join(self.output_dir, "manifest.json")
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        manifest_data = {
            "schemaVersion": 1,
            "dataVersion": data_version,
            "generatedAt": now_iso,
            "packs": pack_specs
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated manifest.json at {manifest_path} with {len(pack_specs)} pack(s) (dataVersion={data_version}).")
        return manifest_path
