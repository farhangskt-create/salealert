# Operating Cost & Quota Control Report

## Architecture Cost Profile
- **Client Cloud Queries**: **$0.00 / month**. Ordinary search, category filtering, sorting, distance calculation, and bookmarking execute 100% locally via Room SQLite and SharedPreferences. Zero recurring Firestore read charges per active user.
- **Central Backend Scraper**: Executes once every 36 hours on a server/host. Bounded by strict API search budget gates (max 100 calls/36h).
- **Hosting & CDN**: Static compressed JSON packs (`.json.gz`) hosted on static object storage (Cloudflare R2 or equivalent). Bandwidth consumption is minimal due to gzip compression and client-side 7-day caching rules.
