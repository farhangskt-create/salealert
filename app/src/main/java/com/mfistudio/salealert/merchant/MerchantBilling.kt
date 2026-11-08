package com.mfistudio.salealert.merchant

import android.app.Activity
import com.android.billingclient.api.*
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.functions.FirebaseFunctions

/** Never grants entitlements locally: Google Play token goes to authenticated backend. */
class MerchantBilling(private val activity: Activity, private val onStatus: (String) -> Unit) : PurchasesUpdatedListener {
    companion object {
        val PRODUCTS = listOf("merchant_promo_7d", "merchant_promo_15d", "merchant_promo_30d")
    }
    private val billing = BillingClient.newBuilder(activity).setListener(this).enablePendingPurchases(
        PendingPurchasesParams.newBuilder().enableOneTimeProducts().build()
    ).build()
    private var campaignId: String? = null
    fun connect() {
        billing.startConnection(object : BillingClientStateListener {
            override fun onBillingServiceDisconnected() { onStatus("Google Play disconnected. Try again.") }
            override fun onBillingSetupFinished(result: BillingResult) {
                onStatus(if (result.responseCode == BillingClient.BillingResponseCode.OK) "Google Play connected" else "Billing unavailable: ${result.debugMessage}")
                if (result.responseCode == BillingClient.BillingResponseCode.OK) restoreUnverifiedPurchases()
            }
        })
    }
    fun purchase(productId: String, pendingCampaignId: String) {
        if (productId !in PRODUCTS) { onStatus("Unknown promotion package"); return }
        if (FirebaseAuth.getInstance().currentUser == null) { onStatus("Sign in first"); return }
        campaignId = pendingCampaignId
        val products = listOf(QueryProductDetailsParams.Product.newBuilder()
            .setProductId(productId).setProductType(BillingClient.ProductType.INAPP).build())
        billing.queryProductDetailsAsync(QueryProductDetailsParams.newBuilder().setProductList(products).build()) { result, details ->
            val product = details.firstOrNull()
            if (result.responseCode != BillingClient.BillingResponseCode.OK || product == null) {
                onStatus("Package not configured in Play Console"); return@queryProductDetailsAsync
            }
            val params = BillingFlowParams.newBuilder().setProductDetailsParamsList(
                listOf(BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(product).build())
            ).build()
            activity.runOnUiThread { billing.launchBillingFlow(activity, params) }
        }
    }
    override fun onPurchasesUpdated(result: BillingResult, purchases: MutableList<Purchase>?) {
        if (result.responseCode == BillingClient.BillingResponseCode.OK) purchases.orEmpty().forEach(::submitPurchase)
        else if (result.responseCode != BillingClient.BillingResponseCode.USER_CANCELED) onStatus("Purchase error: ${result.debugMessage}")
    }
    private fun restoreUnverifiedPurchases() {
        billing.queryPurchasesAsync(QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build()) { result, purchases ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) purchases.forEach(::submitPurchase)
        }
    }
    private fun submitPurchase(purchase: Purchase) {
        if (purchase.purchaseState != Purchase.PurchaseState.PURCHASED) {
            onStatus("Payment pending; promotion not activated"); return
        }
        val cid = campaignId ?: run { onStatus("Purchase detected. Open your campaign to complete verification."); return }
        val productId = purchase.products.firstOrNull() ?: return
        val payload = hashMapOf("campaignId" to cid, "productId" to productId, "purchaseToken" to purchase.purchaseToken)
        FirebaseFunctions.getInstance().getHttpsCallable("verifyMerchantPromotion").call(payload)
            .addOnSuccessListener { onStatus("Payment verified by server; campaign awaits moderation") }
            .addOnFailureListener { onStatus("Verification pending: ${it.localizedMessage}") }
        // Backend owns acknowledgement, refunds and entitlement; never acknowledge or approve here.
    }
    fun close() { billing.endConnection() }
}
