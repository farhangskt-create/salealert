# Sale Alert / BachatBazaar — Source Recovery & Validation (8 Nov 2026)

## Basis
This archive was reconstructed from the uploaded `BachatBazaar_Phase5_Final.zip` (89 files). Sixteen missing scraper-related source/documentation files were restored from the earlier `SaleAlert_LowCost_36Hour_Weekly_Feed.zip`, without overwriting newer files. Android application ID remains `com.mfistudio.salealert`; Room database version has not been changed.

## Verified fixes
- Missing scraper imports restored: `run_due.py`, `search_budget.py`, `parsers/`, `validators/`, `storage/db.py`, `config/sources.json`, `requirements.txt`, and support files.
- 8 Python scraper unit tests passed (`python -m unittest discover -s tests -p 'test_*.py'`). Python syntax compilation passed.
- Android periodic shared-feed polling interval corrected from **24 hours** to **7 days**. `ExistingPeriodicWorkPolicy.UPDATE` replaces an existing 24-hour periodic schedule on app startup.
- Android app triggers a one-time feed fetch on first startup if a CDN URL is configured. Subsequent launch-triggered attempts are throttled locally to at most one per 7 days. WorkManager background schedule is best-effort, not exact.
- The display accepts active deals with no explicit expiry timestamp, matching Room's `expiryTime IS NULL` rule. `Expiring Soon` puts unknown expiry last.
- Expired records are still hidden; there are no fabricated offers.

## Critical BLOCKERS (verified)
1. `dealsCdnBaseUrl` is **not configured** in `gradle.properties`. The Android worker cannot retrieve a remote feed until you configure an HTTPS hosting endpoint and rebuild the APK.
2. On a local run, all configured source statuses were `pending_authorization` or `discovery_required`, so **zero** offers were scraped. The scraper correctly exits 2 without overwriting a previously good feed.
3. `output/manifest.json` does not exist. No published data pack exists in the supplied source archive.
4. Google Search API discovery is **not connected**. The `search_budget.py` module is a budget gate only and has no API adapter/credentials. The claim of 100 free queries requires verification with the actual provider's quota and billing settings.
5. The collector `run_due.py` supports at-most-once-per-36-hours execution on a single host, but an external scheduler (cron / Windows Task Scheduler) and an HTTPS feed publisher/CDN still need deployment.
6. The offer goal of 100 genuine active records is not fulfilled: current verified published offer count is zero.
7. **Android compile, installation and real-device testing have NOT been performed in this environment.** The user's original ZIP reported a successful Android build before restoration; it does not validate these modifications.

## Run and verify the central pipeline
From `sale-alert-scraper`:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py"
python run_due.py --status
python run_due.py
python check_published_feed.py output
```

Before live collection, populate `config/sources.json` with actual permitted feeds and source authorization metadata, deploy an actual search API adapter (server-side only, after billing/quota confirmation), and arrange server-side execution of `run_due.py` at least hourly so that its internal 36-hour gate can run when due. Host the generated `manifest.json` and `packs/*.json.gz` via a shared HTTPS endpoint, and set `dealsCdnBaseUrl` in a private Gradle configuration. Never package search API keys in the Android app. An Android release cannot search the open web merely because its Kotlin build succeeds.

**Cost / timeliness caveat:** A seven-day device refresh minimizes bandwidth, but some 11.11 or one-day promotions can expire before that device sees them. Decide on a lower-cost event-triggered refresh if very short-lived sales must be displayed promptly.

## Safety
The new ZIP intentionally omits `local.properties` (personal machine SDK path), release R8 mapping, build outputs, caches, databases and API secrets. The original uploader's Firebase `google-services.json` remains in the Android source as supplied; it was not replaced or reconfigured. Do not blindly overwrite your existing Windows project; unzip into a NEW directory and compare before importing.
