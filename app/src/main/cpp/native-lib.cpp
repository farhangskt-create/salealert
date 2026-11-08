#include <jni.h>
#include <string>
#include <regex>
#include <exception>
#include <android/log.h>

#define LOG_TAG "NativeScraper"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

/**
 * Native C++ JNI Implementation for Sale Alert Scraper Engine.
 *
 * JNI Method: Java_com_example_salealert_NativeScraperBridge_nativeCheckSaleKeyword
 *
 * Evaluates raw HTML string content against high-performance regex triggers
 * for promotional discount signals (sale, discount, bogo, flat % off, clearance).
 *
 * Compiled with 16 KB page-alignment flags (-Wl,-z,max-page-size=16384)
 * and guaranteed JNI memory release via ReleaseStringUTFChars.
 */
extern "C" JNIEXPORT jboolean JNICALL
Java_com_example_salealert_NativeScraperBridge_nativeCheckSaleKeyword(
        JNIEnv* env,
        jobject /* thiz */,
        jstring htmlContent) {

    if (htmlContent == nullptr) {
        LOGE("Passed null htmlContent to nativeCheckSaleKeyword");
        return JNI_FALSE;
    }

    // Safely acquire C-style UTF-8 string from Java jstring
    const char* nativeHtml = env->GetStringUTFChars(htmlContent, nullptr);
    if (nativeHtml == nullptr) {
        LOGE("Failed to allocate memory for GetStringUTFChars");
        return JNI_FALSE; // Out of memory
    }

    jboolean isSaleDetected = JNI_FALSE;

    try {
        std::string htmlStr(nativeHtml);

        // High-speed case-insensitive regex pattern for promotional triggers
        std::regex salePattern(
            R"((sale|flat\s*\d+%|clearance|discount|blessed\s*friday|bogo|deals|flat\s*off))",
            std::regex::icase | std::regex::ECMAScript
        );

        if (std::regex_search(htmlStr, salePattern)) {
            LOGI("Sale keyword match found in HTML content!");
            isSaleDetected = JNI_TRUE;
        } else {
            LOGI("No sale keywords detected in HTML content.");
        }
    } catch (const std::exception& ex) {
        LOGE("Exception caught in C++ nativeCheckSaleKeyword: %s", ex.what());
        isSaleDetected = JNI_FALSE;
    } catch (...) {
        LOGE("Unknown native exception occurred during regex evaluation");
        isSaleDetected = JNI_FALSE;
    }

    // MANDATORY: Always release string resource to prevent JNI heap memory leaks
    env->ReleaseStringUTFChars(htmlContent, nativeHtml);

    return isSaleDetected;
}
