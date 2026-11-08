# Sale Alert — Deal visibility restoration audit (2026-11-08)

## Confirmed source-code faults addressed

1. Android database includes active offers with null expiry, but `MainActivity` previously filtered them using `expiryTimestamp > now`, thus dropping all null-expiry offers. Fixed.
2. Home and Discover now obtain up to 500 active records across national/merchant sources; the previous 100-record limit could hide a portion of the catalog. For larger catalogs implement paging rather than an unbounded query.
3. `Latest` now orders on feed `lastUpdated`, and `Expiring Soon` puts offers with no expiry after dated offers.
4. Scraper export now refuses to overwrite the existing published feed with an empty output when no verified publishable offers exist.
5. Home shows feed configuration vs no-active-offers diagnoses instead of implying a configured server feed.
6. `sources.json` now includes brand/category/local-store *monitoring candidates*. These are **not approved**, are **not scraped** and are **not advertised as live sales**. Official/authorized feed URLs, source permissions and evidence must be established for each candidate. Facebook access may require approved platform APIs/permissions.

## Operational blockers, not fixed by UI code

- `gradle.properties` does not contain `dealsCdnBaseUrl`. The Android app therefore does not schedule the feed sync unless this Gradle property is supplied at build time.
- All pre-existing scraper sources are `pending_authorization`. There is no basis to activate them automatically.
- This project ZIP contains no published, verified current sales manifest/packs. No November 11 promotional offers have been asserted or invented.
- The scraper requires reviewed/approved source evidence before export, and the generated `output/` directory must be uploaded to a real HTTPS CDN.
- Current app uses a capped 500-row snapshot, not complete server-side paging; large feeds should use incremental pagination.
- No Android SDK/Gradle release build or Samsung device validation has been performed in this container.

## How to restore verified nationwide offers

1. Confirm authorization/source access and add an official feed to each approved source in `sale-alert-scraper/config/sources.json`. Do not mark sources approved without permission.
2. Run `python -m unittest discover -s tests -v` from `sale-alert-scraper/`.
3. Run `python main.py` only after source approvals, and review candidate deals in the admin approval queue. Re-run after approvals to export `output/manifest.json` and data packs.
4. Deploy this `output/` directory at a public HTTPS CDN URL and pass `-PdealsCdnBaseUrl=https://your-actual-host/path` to Gradle or put an appropriate URL in private build configuration.
5. Verify `manifest.json`, pack checksum, 200 status and loaded deals on a real device. Don't clear app data in the process.
6. Run Android Studio `:app:compileDebugKotlin`, `:app:testDebugUnitTest`, `:app:assembleDebug`.

## Existing project protections
Application ID `com.mfistudio.salealert` and Room schema version 1 unchanged. No fictional prices, unverified promotions or live AdMob unit IDs introduced.
