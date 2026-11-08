package com.example.salealert

import android.net.Uri

/**
 * Singleton helper to intercept deal store URLs before they are opened in Chrome Custom Tabs
 * and automatically parse outbound URLs to append tracking parameters or convert them to publisher tracking links.
 */
object AffiliateLinkManager {
    private const val DARAZ_AFFILIATE_ID = "YOUR_DARAZ_AFFILIATE_ID"
    private const val IMPACT_AFFILIATE_ID = "YOUR_IMPACT_AFFILIATE_ID"

    fun transformToAffiliateUrl(originalUrl: String): String {
        if (originalUrl.isBlank()) return originalUrl
        return try {
            val uri = Uri.parse(originalUrl)
            val host = uri.host?.lowercase() ?: return originalUrl

            when {
                host.contains("daraz.pk") -> {
                    // Daraz PK: Append site_id parameter
                    val builder = uri.buildUpon()
                    if (uri.getQueryParameter("site_id") == null) {
                        builder.appendQueryParameter("site_id", DARAZ_AFFILIATE_ID)
                    }
                    builder.build().toString()
                }
                host.contains("impact.com") || host.contains("cj.com") || host.contains("fashion") || host.contains("brand") -> {
                    // Major Fashion / Retail Brands (Impact / CJ Affiliate): Wrap direct store URLs in publisher tracking parameters
                    val builder = uri.buildUpon()
                    if (uri.getQueryParameter("aff_id") == null) {
                        builder.appendQueryParameter("aff_id", IMPACT_AFFILIATE_ID)
                    }
                    builder.build().toString()
                }
                else -> {
                    // Fallback: Return the original URL unchanged if no affiliate program is registered for that specific brand domain
                    originalUrl
                }
            }
        } catch (e: Exception) {
            originalUrl
        }
    }
}
