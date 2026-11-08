# Sale Alert / BachatBazaar Deployment Guide

## 1. Central Backend Scraper & Scheduler
1. Deploy Python backend (`sale-alert-scraper/`) to a server or scheduled environment (e.g. cron job or Windows Task Scheduler running hourly).
2. Configure authorized brand sources in `sale-alert-scraper/config/sources.json`.
3. Set up search API credentials and environment variables securely on the server.
4. Run `python run_due.py` hourly. It executes `main.py` at most once every 36 hours.
5. Publish generated output (`output/manifest.json` and `output/packs/*.json.gz`) to public object storage / CDN.

## 2. Android App Configuration
1. Configure `dealsCdnBaseUrl` in user Gradle properties (`gradle.properties`):
   ```properties
   dealsCdnBaseUrl=https://your-cdn-domain.com
   ```
2. Build signed release AAB:
   ```bash
   ./gradlew :app:bundleRelease
   ```
3. Upload signed AAB to Google Play Console.
