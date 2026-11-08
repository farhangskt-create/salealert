# ==============================================================================
# Sale Alert - ProGuard / R8 Obfuscation Rules
# Target SDK 36, ~30% code shrinking safety & JNI Native Protection
# ==============================================================================

# 1. Keep Native Methods & JNI Bridge
-keepclasseswithmembernames class * {
    native <methods>;
}

-keep class com.example.salealert.NativeScraperBridge {
    *;
}

# 2. Keep Room Database Entities, DAOs & Serialized Fields
-keepclassmembers class com.example.salealert.db.** { *; }
-keep class com.example.salealert.db.** { *; }
-keepclassmembers class com.example.salealert.models.** { *; }
-keep class com.example.salealert.models.** { *; }

# 3. Keep WorkManager & Background Service Classes
-keep class * extends androidx.work.ListenableWorker {
    <init>(...);
}

-keep class com.example.salealert.SaleCheckWorker {
    <init>(...);
}

# 4. Keep Play Services Location & OkHttp Interfaces
-dontwarn com.google.android.gms.location.**
-keep class com.google.android.gms.location.** { *; }

-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }

# 5. R8 Optimization Tuning
-optimizationpasses 5
-dontusemixedcaseclassnames
-verbose
