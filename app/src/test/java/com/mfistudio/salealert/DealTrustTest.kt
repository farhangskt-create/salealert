package com.mfistudio.salealert

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DealTrustTest {
    @Test
    fun urlValidationAllowsOnlyHttpsHostsWithoutCredentials() {
        assertTrue(isValidUrl("store.example.pk/sale"))
        assertFalse(isValidUrl("http://store.example.pk/sale"))
        assertFalse(isValidUrl("javascript:alert(1)"))
        assertFalse(isValidUrl("https://trusted.example@attacker.example"))
        assertFalse(isValidUrl("not a url"))
    }

    @Test
    fun coordinateValidationRejectsMissingAndOutOfRangeLocations() {
        assertTrue(hasValidCoordinates(32.4945, 74.5229))
        assertFalse(hasValidCoordinates(0.0, 0.0))
        assertFalse(hasValidCoordinates(91.0, 74.0))
        assertFalse(hasValidCoordinates(Double.NaN, 74.0))
        assertNull(getCityCoordinates("Unknown city"))
    }

    @Test
    fun discountIsShownOnlyForRecentVerifiedConsistentPrices() {
        val now = System.currentTimeMillis()
        val verified = Deal(
            originalPrice = 5_000.0,
            salePrice = 3_000.0,
            verifiedAt = now
        )
        val unverified = Deal(originalPrice = 5_000.0, salePrice = 3_000.0)
        val inconsistent = Deal(
            originalPrice = 5_000.0,
            salePrice = 5_000.0,
            verifiedAt = now
        )
        val stale = Deal(
            originalPrice = 5_000.0,
            salePrice = 3_000.0,
            verifiedAt = now - 8L * 24 * 60 * 60 * 1000
        )

        assertEquals(40, verified.verifiedDiscountPercent)
        assertNull(unverified.verifiedDiscountPercent)
        assertNull(inconsistent.verifiedDiscountPercent)
        assertNull(stale.verifiedDiscountPercent)
    }
}
