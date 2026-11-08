package com.mfistudio.salealert.data.repository

import com.mfistudio.salealert.data.local.DealEntity
import com.mfistudio.salealert.data.local.SaleAlertDatabase
import com.mfistudio.salealert.Deal
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class DealRepository(private val database: SaleAlertDatabase) {
    fun observeDeals(
        query: String,
        category: String?,
        city: String?,
        isBrand: Boolean?,
        limit: Int = PAGE_SIZE,
        offset: Int = 0
    ): Flow<List<Deal>> = database.dealDao().observeDeals(
        now = System.currentTimeMillis(),
        query = query.trim(),
        category = category,
        city = city,
        isBrand = isBrand,
        limit = limit.coerceIn(1, MAX_PAGE_SIZE),
        offset = offset.coerceAtLeast(0)
    ).map { entities -> entities.map { entity -> entity.toDeal() } }

    private fun DealEntity.toDeal() = Deal(
        id = dealId,
        shopName = shopName,
        title = title,
        discount = 0,
        originalPrice = originalPrice,
        salePrice = salePrice,
        verifiedAt = verifiedAt,
        currency = currency,
        category = categoryId,
        city = cityId.orEmpty(),
        address = address.orEmpty(),
        imageUrl = imageUrl.orEmpty(),
        expiryTimestamp = expiryTime ?: 0L,
        badge = if (isSponsored) "Sponsored" else "Offer",
        url = sourceUrl.orEmpty(),
        status = status,
        isBrand = sourceType != "merchant",
        latitude = latitude ?: 0.0,
        longitude = longitude ?: 0.0
    )

    companion object {
        const val PAGE_SIZE = 50
        const val MAX_PAGE_SIZE = 100
    }
}
