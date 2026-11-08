# Sale Alert Cloudflare Connection — Project File

**Cloudflare project:** https://sale-alert-feed.pages.dev

`gradle.properties` sets `dealsCdnBaseUrl=https://sale-alert-feed.pages.dev`. The existing `app/build.gradle.kts` reads this Gradle property and passes it into `BuildConfig.DEALS_CDN_BASE_URL`; `StaticDealsSyncWorker` downloads `manifest.json` and the referenced gzip packs.

## Integration
1. BACK UP `C:\Users\USER\AndroidStudioProjects\BachatBazaar`.
2. Compare this ZIP against your current project. Do NOT blindly overwrite user edits or delete directories.
3. Copy the single new `dealsCdnBaseUrl=...` line to your current project `gradle.properties`; no need to replace all files if previous Cloudflare Lite version was already applied.
4. In Cloudflare Pages, upload `SaleAlert_Cloudflare_Pages_Ready_Feed.zip` **to the existing `sale-alert-feed` project** using Create new deployment -> Production.
5. Check `https://sale-alert-feed.pages.dev/manifest.json` in browser; current bootstrap pack is intentionally empty (`deals: []`).
6. Sync Gradle and build/install with Android Studio. Verify feed downloads in Logcat (tag DealsSyncWorker).
7. Before Play Store release, publish genuine approved deals with `sale-alert-scraper/community/publish_reviewed_csv.py`, and test on a real device. An empty feed cannot substantiate a live sale discovery product.

**Security:** No search API key is required for static feed access. Never upload the Android source ZIP, google-services.json or CSV review notes to public Pages assets.

**Not completed automatically:** Cloudflare account upload, public live endpoint check, Android Gradle/device run, sourcing and verification of real offers, trader portal, Play Store approval.
