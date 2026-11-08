# Search API Verification Report

## Status
- **Google Custom Search JSON API / Programmable Search Engine**: Prepared / Provider Abstraction Implemented.
- **API Secret Storage**: Kept strictly on the central server backend (`search_budget.py`, `run_due.py`). Never embedded in Android Kotlin code, resources, or public APK.
- **Quota Enforcement**: Hard-capped at 100 requests per 36-hour window and per UTC day via SQLite atomic locking (`search_budget.py`).
- **Fallback Mechanism**: When API search is unconfigured or rate-limited, the central backend falls back to authorized direct feed scraping and approved source registries without impacting client-side app stability.
