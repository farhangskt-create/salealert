# Sale Alert: low-cost central search and >=100 genuine deals target

## Required operation (not automatically deployed)

1. A **single hosted collector** is polled by a server scheduler, but runs at most once every **36 hours** (`run_due.py`). Users' phones never invoke web search.
2. The existing `main.py` only fetches sources marked `approved`. A legacy Google Search/Custom Search integration and API credentials **are not currently present**. To restore discovery, connect an authorized search provider to the server pipeline; use `search_budget.reserve_search()` before every billable search. The included module provides a conservative hard cap of **100 reserved searches in a rolling 36-hour window AND per UTC day**, not a guarantee of 100 free provider requests. Check the provider's actual pricing and quotas first. A failed search still consumes the reserved budget by design.
3. Discovery searches identify candidate official brand promotions, not verified offers. Evidence, dates, eligibility and approval are required before publication. Scraping other sites/social posts must comply with their access rules. Do not manufacture discount percentages or 11.11 offers.
4. The central database can retain many sources and verified deals. `check_published_feed.py output` reports the **100 genuine-offer target gap**. Fewer than 100 verified offers are displayed honestly; no artificial padding. `sources.json` is a watchlist, not a working 100-brand integration.
5. A single **public HTTPS static feed** (manifest + packs) is published from the server to a low-cost static CDN/object store, using separate deployment infrastructure. `dealsCdnBaseUrl` must point to its root. Credentials and real endpoints are not included in the ZIP.
6. Android phones check the shared feed approximately **once every 7 days**, including catch-up after the app opens if it is due. WorkManager timing is inexact; failed requests can retry. Room database keeps old offers offline, but expired offers stay hidden. Pack checksums prevent downloads when unchanged. **App users never call the search API.**
7. Trade-off: 7-day client checks mean a 36-hour central discovery might not appear on a given phone for up to a week. For timely 11.11 offers, consider a narrowly scoped opt-in urgent refresh or a shorter interval. Do not claim real-time alerts with weekly sync.

## Rollout checklist
- [ ] Authorized discovery provider added and connected to `reserve_search()` (NOT implemented here)
- [ ] Verified sources approved and populated; aim for 100+ real offers (NOT currently achieved)
- [ ] Server scheduler deployed and monitoring alerts added (NOT deployed)
- [ ] Public HTTPS CDN deployed and `dealsCdnBaseUrl` configured (NOT deployed)
- [ ] Device APK compiled and end-to-end sync validated (NOT tested here)
