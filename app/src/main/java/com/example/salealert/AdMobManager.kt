package com.example.salealert

import android.app.Activity
import android.content.Context
import android.util.Log
import com.google.android.gms.ads.AdError
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.FullScreenContentCallback
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.interstitial.InterstitialAd
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback
import java.util.concurrent.atomic.AtomicInteger

/**
 * Manages Google Mobile Ads (AdMob) Interstitial Ads pre-loading, thread-safe click counting,
 * and frequency capping (displaying once every 3 to 4 deal clicks).
 */
object AdMobManager {
    private const val TAG = "AdMobManager"
    private const val INTERSTITIAL_AD_UNIT_ID = "ca-app-pub-3940256099942544/1033173712" // Google Test Ad ID

    private var interstitialAd: InterstitialAd? = null
    private var isLoadingAd = false
    private val clickCounter = AtomicInteger(0)
    private const val FREQUENCY_CAP = 3 // Show interstitial every 3rd deal click

    fun loadInterstitial(context: Context) {
        if (interstitialAd != null || isLoadingAd) return
        isLoadingAd = true
        val adRequest = AdRequest.Builder().build()
        InterstitialAd.load(
            context.applicationContext,
            INTERSTITIAL_AD_UNIT_ID,
            adRequest,
            object : InterstitialAdLoadCallback() {
                override fun onAdLoaded(ad: InterstitialAd) {
                    interstitialAd = ad
                    isLoadingAd = false
                    Log.d(TAG, "Interstitial ad loaded successfully.")
                }

                override fun onAdFailedToLoad(error: LoadAdError) {
                    interstitialAd = null
                    isLoadingAd = false
                    Log.d(TAG, "Interstitial ad failed to load: ${error.message}")
                }
            }
        )
    }

    fun showAdOnDealClick(activity: Activity, onComplete: () -> Unit) {
        val currentClicks = clickCounter.incrementAndGet()
        Log.d(TAG, "Deal click count: $currentClicks")

        if (currentClicks >= FREQUENCY_CAP && interstitialAd != null) {
            clickCounter.set(0) // Reset counter
            val ad = interstitialAd
            interstitialAd = null // Consume ad
            loadInterstitial(activity) // Pre-load next one

            ad?.fullScreenContentCallback = object : FullScreenContentCallback() {
                override fun onAdDismissedFullScreenContent() {
                    onComplete()
                }

                override fun onAdFailedToShowFullScreenContent(adError: AdError) {
                    onComplete()
                }
            }
            ad?.show(activity)
        } else {
            if (interstitialAd == null) {
                loadInterstitial(activity)
            }
            onComplete()
        }
    }
}
