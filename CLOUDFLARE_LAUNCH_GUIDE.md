# Sale Alert — low-cost Cloudflare Pages feed (implementation package)

## Already implemented
- Existing Android app retains its 7-day WorkManager sync, Room offline cache, gzip/SHA-256 verification and all five screens. No Google Search API is needed for this mode.
- Added `sale-alert-scraper/community/publish_reviewed_csv.py`: a **manual admin-reviewed CSV importer** that publishes the same manifest/pack schema Android already understands.
- It rejects missing evidence, stale verification, expired deals, duplicate IDs and invalid prices. It does **not** verify URLs automatically: an administrator must check the real offer before setting `approval=approved`.
- No automatic web scraping, fake deals or API keys are required. No trader login/online submission portal is implemented by this package.

## Publish the feed — four steps
1. Open `sale-alert-scraper/community/deals_template.csv` in Excel. Fill the rows with **real** offers. Set `approval=approved` only after checking the merchant's offer and keeping an evidence note. `expiryTime` and `verifiedAt` are Unix **milliseconds**; `verifiedAt` must be within the last 7 days. Source URLs must be HTTPS. Leave `approval=pending` for unreviewed offers.
2. Run from the project root:
   `python sale-alert-scraper/community/publish_reviewed_csv.py --csv sale-alert-scraper/community/deals_template.csv --out cloudflare-public`
   The blank template intentionally cannot produce a live feed. Add verified offers first.
3. In Cloudflare dashboard create a **Pages** project using **Direct Upload**; upload the *contents* of `cloudflare-public` as static assets. Verify `https://YOUR-PAGES-SITE.pages.dev/manifest.json` and the `packs/...json.gz` URL load. Cloudflare account creation and upload must be done by the owner; no credentials are in this ZIP. If publishing updated packs, upload all files and publish the manifest last when possible.
4. In Android Studio add to your **local** `gradle.properties` (or user Gradle properties):
   `dealsCdnBaseUrl=https://YOUR-PAGES-SITE.pages.dev`
   Sync Gradle, build and install; test first-launch download and offline cache. Do not ship a release with placeholder URL.

## Important operational rules
- Review and re-publish deals frequently (daily recommended). The Android client checks on first launch and normally every 7 days; a shorter client refresh needs a deliberate product/cost change.
- An unexpired offer can still become invalid early: admin must remove it from CSV and republish. Do not imply that this system automatically checks live merchant offers.
- For zero active deals, the publisher fails without overwriting the last published manifest. Android locally hides expired offers. To intentionally clear old unexpired offers, publish a reviewed withdrawal/tombstone workflow before production; the current tool deliberately does not publish empty feeds.
- Public feed only: **do not upload** `.env`, `google-services.json`, databases, local CSV review notes or the project ZIP to Cloudflare Pages.
- Cloudflare free tier is subject to current terms, service quotas, and abuse limits. User acquisition, deal verification, privacy-policy URL, Play Console declarations, signing and release testing remain owner responsibilities.
- App Store ranking cannot be guaranteed by code changes; accurate store metadata, quality and retention are necessary.

## Verification
From `sale-alert-scraper`: `python -m unittest discover -s tests -p 'test_*.py'`
When a feed has been created: `python check_published_feed.py ../cloudflare-public`

## What remains blocked / not implemented
- A real public Cloudflare Pages deployment and URL (requires account owner).
- Live, admin-verified offers and ongoing sourcing.
- Self-service trader accounts, authenticated submission, moderation dashboard and notifications (not represented as complete).
- Real Android Studio build/device tests on the owner's Windows machine and Google Play release checks.
