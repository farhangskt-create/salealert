# Sale Alert — Central collection every 36 hours

## Exactly who does what?

- **One hosted Python collector** runs `python run_due.py` from `sale-alert-scraper` every hour using a server scheduler. `run_due.py` only performs the actual scrape once per **36 elapsed hours**, using a SQLite run-state lock. There is **no crawler on users' phones**.
- It reads `config/sources.json`, fetches only approved/configured sources, validates and stores candidates in central SQLite. Deals require genuine source evidence and approval prior to publication.
- If approved publishable offers exist, `main.py` creates `output/manifest.json` and compressed pack files. **A separate deployment step must upload the output to a public HTTPS host.** This repo does not contain hosting credentials or a live deployment implementation.
- Android phones download this one shared verified feed using WorkManager (36-hour periodic schedule, plus app-launch catch-up), and cache it in the existing Room database. The worker skips network transfer when last successful check is newer than 36h; checksums and pack versions prevent redundant pack downloads. A device can display existing cached offers offline (subject to expiry).
- **Current missing dependencies:** An actual always-on server or scheduled job, approved usable sources, any historical Google search API integration and its credentials, publishing to real HTTPS CDN, and `dealsCdnBaseUrl` in the Android build. Without these, no automatic *new* live deals will appear.
- Google search is NOT performed by Firebase Analytics, Google Play, or Android WorkManager. If an authorized Google search discovery service is desired it needs its own paid/authorized provider API, key, quotas, and result verification; do not embed API keys in the Android app.

## How to schedule on Windows (server PC must be online)
Run once in an elevated PowerShell / cmd shell (adjust path):

`SCHTASKS /Create /SC HOURLY /TN SaleAlertCentralCollector /TR "C:\path\to\sale-alert-scraper\run_due_hourly.bat" /F`

On Linux server cron: `0 * * * * cd /opt/sale-alert/sale-alert-scraper && /usr/bin/python3 run_due.py >> collector.log 2>&1`

**Scheduling is not configured simply by downloading a ZIP.** The external host, network access, approvals, and CDN publishing must still be set up. Android 36h is inexact because Android WorkManager is OS-managed. User launch catch-up is scheduled subject to connectivity, but uses the same 36h successful-check guard.

## Safety & limitations
- No fabricated discounts or unverified 11.11 promotions.
- Do not set `permission_status=approved` without appropriate source rights and evidence.
- Empty/failed collection does not overwrite the previous exported feed.
- Runs are limited to once every 36h even after a failure; a repeated attempt occurs at the next window. `--status` shows run state.
- Multiple hosts sharing the same source need a single centralized scheduler or shared state; local SQLite is not a distributed lock.
