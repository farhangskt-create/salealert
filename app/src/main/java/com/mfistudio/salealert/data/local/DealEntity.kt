package com.mfistudio.salealert.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "deals",
    indices = [
        Index(value = ["sourcePackId"]),
        Index(value = ["categoryId", "cityId", "status"]),
        Index(value = ["expiryTime"]),
        Index(value = ["lastUpdated"])
    ]
)
data class DealEntity(
    @PrimaryKey val dealId: String,
    val merchantId: String?,
    val shopName: String,
    val title: String,
    val description: String?,
    val address: String?,
    val categoryId: String,
    val cityId: String?,
    val originalPrice: Double?,
    val salePrice: Double?,
    val currency: String?,
    val imageUrl: String?,
    val sourceUrl: String?,
    val latitude: Double?,
    val longitude: Double?,
    val startTime: Long?,
    val expiryTime: Long?,
    val verifiedAt: Long?,
    val sourceType: String,
    val isSponsored: Boolean,
    val lastUpdated: Long,
    val status: String,
    val sourcePackId: String
)
