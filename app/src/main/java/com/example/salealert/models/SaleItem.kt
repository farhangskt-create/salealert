package com.example.salealert.models

import androidx.annotation.Keep

/**
 * Data model class representing a sales or discount item.
 */
@Keep
data class SaleItem(
    val title: String,
    val storeName: String,
    val category: String, // "Food", "Clothes", "Other Shopping"
    val discountBadge: String, // e.g. "FLAT 50% OFF", "BOGO DEAL"
    val storeUrl: String,
    val locationContext: String = ""
)
