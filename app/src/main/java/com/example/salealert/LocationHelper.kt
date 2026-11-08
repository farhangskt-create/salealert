package com.example.salealert

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Geocoder
import android.os.Build
import android.util.Log
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import java.util.Locale

/**
 * Thread-safe Location Helper class utilizing Google Play Services FusedLocationProviderClient.
 * Fetches user location coordinates and reverse-geocodes locality on Dispatchers.IO.
 */
class LocationHelper(private val context: Context) {

    companion object {
        private const val TAG = "LocationHelper"
    }

    private val fusedLocationClient: FusedLocationProviderClient by lazy {
        LocationServices.getFusedLocationProviderClient(context)
    }

    /**
     * Checks if location permissions are granted.
     */
    fun hasLocationPermission(): Boolean {
        val fineLocation = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        val coarseLocation = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        return fineLocation || coarseLocation
    }

    /**
     * Fetches current location city/locality string safely on Dispatchers.IO.
     * Never blocks the Main Thread.
     */
    suspend fun getCurrentCityName(): String = withContext(Dispatchers.IO) {
        if (!hasLocationPermission()) {
            Log.w(TAG, "Location permission not granted. Returning default locality.")
            return@withContext "Nearby"
        }

        try {
            val cancellationTokenSource = CancellationTokenSource()
            val location = fusedLocationClient.getCurrentLocation(
                Priority.PRIORITY_BALANCED_POWER_ACCURACY,
                cancellationTokenSource.token
            ).await()

            if (location != null) {
                val geocoder = Geocoder(context, Locale.getDefault())
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    var cityName = "Nearby"
                    geocoder.getFromLocation(location.latitude, location.longitude, 1) { addresses ->
                        if (addresses.isNotEmpty()) {
                            cityName = addresses[0].locality
                                ?: addresses[0].subAdminArea
                                ?: addresses[0].adminArea
                                ?: "Nearby"
                        }
                    }
                    return@withContext cityName
                } else {
                    @Suppress("DEPRECATION")
                    val addresses = geocoder.getFromLocation(location.latitude, location.longitude, 1)
                    if (!addresses.isNullOrEmpty()) {
                        val locality = addresses[0].locality
                            ?: addresses[0].subAdminArea
                            ?: addresses[0].adminArea
                        if (!locality.isNullOrEmpty()) {
                            return@withContext locality
                        }
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching location or geocoding", e)
        }

        return@withContext "Nearby"
    }
}
