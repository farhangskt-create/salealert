package com.example.salealert

import androidx.annotation.Keep

/**
 * Thread-safe Kotlin bridge for C++ NDK library `libnative-scraper.so`.
 * Annotated with @Keep to prevent R8 obfuscation from mangling JNI method names.
 */
@Keep
object NativeScraperBridge {

    init {
        try {
            System.loadLibrary("native-scraper")
        } catch (e: UnsatisfiedLinkError) {
            e.printStackTrace()
        }
    }

    /**
     * Native C++ JNI declaration.
     * Evaluates raw HTML string on C++ thread safely.
     *
     * @param htmlContent Raw HTML document body.
     * @return true if an active sale keyword pattern is matched.
     */
    @Keep
    external fun nativeCheckSaleKeyword(htmlContent: String): Boolean
}
