"""Audit a local deployed/scraped feed directory without network access.

Usage: python check_published_feed.py output
"""
import gzip
import hashlib
import json
from pathlib import Path
import sys


def main() -> int:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / 'output'
    manifest_file = base / 'manifest.json'
    if not manifest_file.exists():
        print(f'BLOCKED: missing {manifest_file}. No published deals feed is present.')
        return 2
    manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
    assert manifest.get('schemaVersion') == 1, 'unsupported manifest schema'
    packs = manifest.get('packs', [])
    total = 0
    for pack in packs:
        rel = Path(pack['url'])
        assert not rel.is_absolute() and '..' not in rel.parts, 'unsafe pack path'
        payload = (base / rel).read_bytes()
        assert len(payload) == pack['sizeBytes'], 'pack size mismatch'
        assert hashlib.sha256(payload).hexdigest() == pack['sha256'].lower(), 'pack hash mismatch'
        data = json.loads(gzip.decompress(payload))
        assert data['schemaVersion'] == 1, 'unsupported pack schema'
        deals = data.get('deals', [])
        total += len(deals)
        print(f"{pack['id']}: {len(deals)} record(s), SHA-256 verified")
    print(f"TOTAL: {total} verified-format offer record(s) in {len(packs)} pack(s)")
    if total < 100:
        print(f"TARGET GAP: {100-total} more verified active offers needed for the 100-offer goal. No fake offers added.")
    if total == 0:
        print('WARNING: feed currently contains no offers. Do not claim any live sales.')
        return 3
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, OSError, ValueError) as exc:
        print(f'FAIL: {exc}')
        raise SystemExit(1)
