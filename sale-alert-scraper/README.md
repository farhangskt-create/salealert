# Sale Alert — Pakistani Deals Scraper & CDN Data Pack Generator

This standalone Python project scrapes, validates, formats, and exports Pakistani shopping deals into compressed `.json.gz` data packs and a `manifest.json` file.

The generated data pack structure matches the schema required by the Android `StaticDealsSyncWorker.kt`.

---

## 📁 Directory Structure

```
sale-alert-scraper/
├── config/
│   └── sources.json               # Configured deal sources (Daraz, Khaadi, Sialkot, etc.)
├── parsers/
│   ├── base_parser.py             # Abstract base parser interface
│   └── pakistani_deals_parser.py  # Scraper & parser for Pakistani brand & retail feeds
├── validators/
│   └── deal_validator.py          # Strict validator matching Android app worker rules
├── exporters/
│   └── json_pack_exporter.py      # Gzip compressor, SHA-256 checksum & manifest generator
├── output/                        # Generated manifest.json and packs/*.json.gz output folder
├── main.py                        # Main CLI entry point
├── requirements.txt               # Dependencies (requests, beautifulsoup4, urllib3)
└── run_scraper.bat                # One-click Windows execution batch script
```

---

## 🚀 Execution Instructions on Windows

### Option 1: Double-Click Batch Script
Double-click `run_scraper.bat` in File Explorer.

### Option 2: Command Line
Open Command Prompt or PowerShell in `sale-alert-scraper/`:
```cmd
pip install -r requirements.txt
python main.py
```

---

## 📄 Schema & Worker Validation Rules

The generated `manifest.json` and `packs/*.json.gz` files satisfy all rules of `StaticDealsSyncWorker.kt`:

1. **Manifest Schema**:
   - `schemaVersion`: 1
   - `dataVersion`: Monotonically increasing integer
   - `packs`: Array of pack specs (`id`, `version`, `url`, `sha256`, `sizeBytes`)
   - `sha256`: Lowercase 64-character SHA-256 hex checksum of compressed `.json.gz`
   - `sizeBytes`: Exact compressed byte size

2. **Deal Pack Schema**:
   - `schemaVersion`: 1
   - `deals`: List of deal objects matching `DealEntity` required fields:
     - `dealId`, `merchant`, `title`, `categoryId`
     - `originalPrice` & `salePrice` (both present or both null; `originalPrice > salePrice > 0.0`)
     - `currency` (required when prices present, e.g. `"PKR"`)
     - `sourceType`: `"brand"` | `"merchant"` | `"publisher"` | `"affiliate"`
     - `status`: `"active"`
     - `lastUpdated`: Epoch millisecond timestamp
