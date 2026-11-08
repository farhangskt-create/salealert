# Google Play Compliance Checklist

- [x] **Application ID**: Preserved `com.mfistudio.salealert`.
- [x] **Target SDK**: Configured `targetSdk = 36` (Android 16 compatible).
- [x] **Manifest Properties**: Ad Services configuration declaration included with `tools:replace="android:resource"`.
- [x] **Privacy Policy**: Required policy URL entry in Profile screen and Play Console.
- [x] **AdMob UMP Consent**: Configured for EEA/regulated user consent requirements.
- [x] **In-App Review**: Prepared Google Play In-App Review API integration.
- [x] **Data Safety Declaration**: Accurate data collection declarations for Crashlytics, Analytics, and AdMob.
- [x] **R8 Code Shrinking**: Enabled in release build configuration (`isMinifyEnabled = true`, `isShrinkResources = true`).
