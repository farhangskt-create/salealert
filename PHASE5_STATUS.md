# Sale Alert — repaired source package (not release-certified)

## Changes made
- Preserved applicationId `com.mfistudio.salealert` and Room version 1.
- Fixed repository query so Discover and Nearby receive all categories instead of the legacy brand-only tab.
- Removed city-center substitution for GPS distance; Nearby now requires an actual device location.
- Nearby list is independent of Discover search filters.
- Added persisted city selection and a Google Play rating link to Profile.
- Added Firebase Analytics, Crashlytics and Performance Gradle integration; Crashlytics collection disabled in debug builds.
- Added navigation analytics event with no personal information.
- Aligned Compose compiler plugin version to the Kotlin catalog version.
- Disabled eager AdMob initialization until consent integration is complete.

## Still pending (do NOT publish yet)
- Android Gradle compilation, physical device testing and Firebase console event verification were not possible in this environment.
- AdMob UMP consent, production AdMob IDs, ad placement audit, rewarded ad benefit, trader backend, full account deletion and legal/privacy URLs remain pending.
- Play In-App Review automatic dialog is not wired; Profile opens the official Play listing to request a rating.
- The current project has no functional trader account backend; no fictional payment/subscription IDs were created.
- Firebase plugin/SDK versions and existing Android Gradle Plugin version need Android Studio sync validation.
- Verify current Firebase config matches package before building.
- Release signing is NOT included or modified.

## Local build
Open project in Android Studio and sync Gradle. Run `gradlew.bat :app:compileDebugKotlin :app:testDebugUnitTest :app:assembleDebug`. Keep the original project as backup.
