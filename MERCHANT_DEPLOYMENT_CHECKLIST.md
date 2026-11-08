# Sale Alert targeted modernization — 2026-11-08

## What is actually implemented in this source archive

- Kept the existing Android package, Compose navigation, Room, and Cloudflare sync.
- Restored a merchant-facing campaign form and email/password sign-in under Profile > Merchant Dashboard.
- Added Google Play Billing client integration for three **one-time consumable** promotion products.
- Added authenticated Cloud Functions `createMerchantCampaign` and `verifyMerchantPromotion` with Google Android Publisher API purchase verification, token deduplication, and **pending_moderation** state.
- Removed EasyPaisa payment UI from the active merchant flow. Historical old code remains in the legacy `com.example.salealert` source package for preservation and is not the active UI.
- Fixed backend smart scheduler category cursor persistence, empty-search deal-history preservation, API credential gating, bridge import, and search-lead quarantine.
- Preserved Cloudflare/Room public-feed design; no live feed was deployed or changed.
- Updated Discover category chips to match the registry category names.

## Required external configuration before merchant payments can work

1. In Firebase Console, enable **Email/Password Authentication** for the same project as `app/google-services.json`.
2. Deploy Cloud Functions from `firebase-functions/` to the matching Firebase project. Configure IAM/Google Play Developer API service-account access for purchase verification. Functions may incur usage charges; check your plan and quotas.
3. In Google Play Console create **one-time in-app products** with exact IDs `merchant_promo_7d`, `merchant_promo_15d`, `merchant_promo_30d`, set prices there, activate them and test using Play license testers. Products are not subscriptions.
4. Merge `firebase-functions/firestore.rules` into the project's existing Firestore rules; **do not replace other rules blindly**. Restrict campaign/token writes to the Admin SDK.
5. Implement a moderator-only approval tool and public feed export for approved campaigns. **Payment does not automatically publish a deal**.
6. Implement Google Play Real-Time Developer Notifications / refund, voided purchase, and campaign revocation handling. Do not sell production campaigns before this is completed.
7. Configure the existing backend search provider (if authorized), scheduled runner, verified brand URLs, and Cloudflare publishing credentials. Do not place Google search credentials in Android.
8. Test merchant purchases with a Play-distributed test build, not only a sideloaded APK; sign-in and billing require actual Firebase/Play services.

## Verification status

- Python backend: 15 unit tests passed in this container.
- Kotlin/Android: **not compiled in this environment** (Android SDK/Gradle toolchain unavailable). Android Studio compilation and device testing required.
- Google Play Billing: **source integration only**, not tested with live Play products.
- Firebase Functions: **source integration only**, not deployed.
- Live verified deals published: **none demonstrated**.
- No production-ready claim. Old source ZIP and AAB were inspected but not modified.

## Known limitations

- User-created campaigns are saved as drafts and can be purchased only after the Cloud Functions and Play products are configured.
- The merchant screen does not yet list past campaigns or show analytics; implement after verified end-to-end payment tests.
- Merchant images, reviews, fake-sale reports and a moderation dashboard require further code and backend work.
- The old project's Google search function returned hardcoded sample deals; the new scheduler uses the existing server-side Google search bridge only if authorized credentials are configured.
- Firebase reads for public deal browsing are avoided via Cloudflare/Room, but authentication, campaign creation, and moderation use Firebase and may incur billing.
