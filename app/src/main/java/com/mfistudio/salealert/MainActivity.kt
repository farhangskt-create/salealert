package com.mfistudio.salealert

import com.mfistudio.salealert.ui.components.SaleAlertBottomNavBar
import com.mfistudio.salealert.ui.screens.*

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.location.Geocoder
import android.net.Uri
import android.os.Bundle
import android.telephony.TelephonyManager
import android.util.Base64
import android.util.LruCache
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.browser.customtabs.CustomTabsIntent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.basicMarquee
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.AdSize
import com.google.android.gms.ads.AdView
import com.google.android.gms.ads.MobileAds
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.crashlytics.FirebaseCrashlytics
import com.google.android.gms.location.LocationServices
import com.mfistudio.salealert.data.local.SaleAlertDatabase
import com.mfistudio.salealert.data.repository.DealRepository
import com.mfistudio.salealert.workers.StaticDealsSyncWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.URI
import java.text.SimpleDateFormat
import java.util.*

// ==========================================
// UTILITY FUNCTIONS & SANITIZERS
// ==========================================

fun sanitizeUrl(inputUrl: String): String {
    if (inputUrl.isBlank()) return ""
    val candidate = inputUrl.trim().let {
        if (it.contains("://")) it else "https://$it"
    }
    if (candidate.any(Char::isWhitespace)) return ""
    val uri = try {
        URI(candidate)
    } catch (_: Exception) {
        return ""
    }
    if (!uri.scheme.equals("https", ignoreCase = true) ||
        uri.host.isNullOrBlank() ||
        uri.rawUserInfo != null
    ) return ""
    return uri.toASCIIString()
}

fun isValidUrl(url: String): Boolean {
    if (url.isBlank()) return false
    return sanitizeUrl(url).isNotBlank()
}

object BitmapCache {
    private val maxMemory = (Runtime.getRuntime().maxMemory() / 1024).toInt()
    private val cacheSize = maxMemory / 8
    private val cache = object : LruCache<String, Bitmap>(cacheSize) {
        override fun sizeOf(key: String, bitmap: Bitmap): Int {
            return bitmap.byteCount / 1024
        }
    }

    fun get(key: String): Bitmap? = cache.get(key)
    fun put(key: String, bitmap: Bitmap) {
        if (key.isNotBlank()) cache.put(key, bitmap)
    }
}

@Composable
fun rememberDecodedBitmap(base64Str: String): Bitmap? {
    var bitmap by remember(base64Str) { mutableStateOf<Bitmap?>(BitmapCache.get(base64Str)) }

    LaunchedEffect(base64Str) {
        if (base64Str.isNotBlank() && bitmap == null) {
            withContext(Dispatchers.IO) {
                val decoded = try {
                    val decodedBytes = Base64.decode(base64Str, Base64.DEFAULT)
                    BitmapFactory.decodeByteArray(decodedBytes, 0, decodedBytes.size)
                } catch (_: Exception) {
                    null
                }
                if (decoded != null) {
                    BitmapCache.put(base64Str, decoded)
                    withContext(Dispatchers.Main) {
                        bitmap = decoded
                    }
                }
            }
        }
    }
    return bitmap
}

fun extractDomain(urlStr: String, shopName: String): String {
    if (urlStr.isNotBlank()) {
        try {
            val uri = Uri.parse(urlStr)
            val host = uri.host
            if (!host.isNullOrBlank()) {
                return host.removePrefix("www.")
            }
        } catch (_: Exception) {}
    }
    val cleanedShop = shopName.lowercase().replace(" ", "").replace(".", "").replace("'", "")
    return "$cleanedShop.com"
}

@Composable
fun rememberFaviconBitmap(domain: String): Bitmap? {
    val faviconUrl = "https://www.google.com/s2/favicons?domain=$domain&sz=128"
    var bitmap by remember(faviconUrl) { mutableStateOf<Bitmap?>(BitmapCache.get(faviconUrl)) }

    LaunchedEffect(faviconUrl) {
        if (domain.isNotBlank() && bitmap == null) {
            withContext(Dispatchers.IO) {
                try {
                    val client = OkHttpClient()
                    val request = Request.Builder().url(faviconUrl).build()
                    val response = client.newCall(request).execute()
                    if (response.isSuccessful) {
                        val stream = response.body?.byteStream()
                        if (stream != null) {
                            val decoded = BitmapFactory.decodeStream(stream)
                            if (decoded != null) {
                                BitmapCache.put(faviconUrl, decoded)
                                withContext(Dispatchers.Main) {
                                    bitmap = decoded
                                }
                            }
                        }
                    }
                } catch (_: Exception) {}
            }
        }
    }
    return bitmap
}

fun calculateDistanceKm(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val r = 6371.0
    val dLat = Math.toRadians(lat2 - lat1)
    val dLon = Math.toRadians(lon2 - lon1)
    val a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2)
    val c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    return r * c
}

fun hasValidCoordinates(latitude: Double, longitude: Double): Boolean =
    latitude.isFinite() && longitude.isFinite() &&
        latitude in -90.0..90.0 && longitude in -180.0..180.0 &&
        (latitude != 0.0 || longitude != 0.0)

fun getCityCoordinates(city: String): Pair<Double, Double>? {
    return when (city.lowercase().trim()) {
        "sialkot" -> Pair(32.4945, 74.5229)
        "lahore" -> Pair(31.5204, 74.3587)
        "islamabad" -> Pair(33.6844, 73.0479)
        "karachi" -> Pair(24.8607, 67.0011)
        "faisalabad" -> Pair(31.4504, 73.1350)
        "rawalpindi" -> Pair(33.5651, 73.0169)
        "multan" -> Pair(30.1575, 71.5249)
        "gujranwala" -> Pair(32.1877, 74.1945)
        "peshawar" -> Pair(34.0151, 71.5249)
        "quetta" -> Pair(30.1798, 66.9750)
        else -> null
    }
}

fun getUserCountryCode(context: Context): String {
    return try {
        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager
        val simCountry = tm?.simCountryIso?.uppercase()
        if (!simCountry.isNullOrBlank()) {
            simCountry
        } else {
            Locale.getDefault().country.uppercase().ifBlank { "PK" }
        }
    } catch (_: Exception) {
        Locale.getDefault().country.uppercase().ifBlank { "PK" }
    }
}

// ==========================================
// DATA MODEL
// ==========================================

data class Deal(
    val id: String = UUID.randomUUID().toString(),
    val shopName: String = "",
    val title: String = "",
    val discount: Int = 0,
    val originalPrice: Double? = null,
    val salePrice: Double? = null,
    val verifiedAt: Long? = null,
    val currency: String? = null,
    val imageUrl: String = "",
    val category: String = "Food",
    val city: String = "",
    val address: String = "",
    val whatsappNumber: String = "",
    val imageBase64: String = "",
    val packageType: String = "1 Week Package (7 Days)",
    val expiryTimestamp: Long = 0L,
    val isFlashSale: Boolean = false,
    val flashDurationHours: Int = 6,
    val isFreeTrialUsed: Boolean = false,
    val badge: String = "OFFER",
    val url: String = "",
    val status: String = "active",
    val isLocalShop: Boolean = true,
    val distanceKm: Double = 0.0,
    val isBrand: Boolean = false,
    val brandLogoUrlOrBase64: String = "",
    val latitude: Double = 0.0,
    val longitude: Double = 0.0
) {
    val verifiedDiscountPercent: Int?
        get() {
            val verificationTime = verifiedAt ?: return null
            val original = originalPrice ?: return null
            val sale = salePrice ?: return null
            if (verificationTime <= 0L ||
                verificationTime > System.currentTimeMillis() ||
                System.currentTimeMillis() - verificationTime > 7L * 24 * 60 * 60 * 1000 ||
                !original.isFinite() || !sale.isFinite() ||
                original <= 0.0 || sale <= 0.0 || sale >= original
            ) return null
            return (((original - sale) / original) * 100).toInt().takeIf { it > 0 }
        }
}

val countryList = listOf("Pakistan", "UAE", "UK", "USA", "Global")

val provinceMap = mapOf(
    "Pakistan" to listOf("Punjab", "Sindh", "KPK", "Balochistan", "Islamabad Capital Territory", "Gilgit-Baltistan", "AJK"),
    "UAE" to listOf("Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain"),
    "UK" to listOf("England", "Scotland", "Wales", "Northern Ireland"),
    "USA" to listOf("California", "New York", "Texas", "Florida", "Illinois"),
    "Global" to listOf("Worldwide")
)

val pakistanCitiesMap = mapOf(
    "Punjab" to listOf("Sialkot", "Lahore", "Faisalabad", "Rawalpindi", "Multan", "Gujranwala", "Bahawalpur", "Sargodha", "Gujrat", "Sahiwal", "Jhelum", "Rahim Yar Khan", "Sheikhupura", "Kasur", "Okara", "Chiniot", "Kamoke", "Hafizabad", "Sadiqabad", "Burewala", "Khanewal", "Muzaffargarh", "Mandi Bahauddin", "Toba Tek Singh", "Khanpur", "Dera Ghazi Khan"),
    "Sindh" to listOf("Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah", "Mirpur Khas", "Jacobabad", "Shikarpur", "Khairpur", "Dadu", "Tando Adam", "Ghotki", "Badin"),
    "KPK" to listOf("Peshawar", "Abbottabad", "Mardan", "Swat", "Nowshera", "Charsadda", "Bannu", "Kohat", "Dera Ismail Khan", "Mansehra", "Swabi", "Haripur"),
    "Balochistan" to listOf("Quetta", "Gwadar", "Turbat", "Khuzdar", "Sibi", "Loralai", "Zhob", "Chaman", "Kalat", "Panjgur"),
    "Islamabad Capital Territory" to listOf("Islamabad"),
    "Gilgit-Baltistan" to listOf("Gilgit", "Skardu", "Hunza", "Diamer", "Ghizer", "Astore", "Ghanche"),
    "AJK" to listOf("Muzaffarabad", "Mirpur", "Rawalakot", "Kotli", "Bhimber", "Hajira", "Bagh", "Poonch"),
    "Dubai" to listOf("Dubai City", "Deira", "Bur Dubai", "Jumeirah", "Downtown Dubai"),
    "Abu Dhabi" to listOf("Abu Dhabi City", "Al Ain", "Madinat Zayed"),
    "Sharjah" to listOf("Sharjah City", "Khor Fakkan", "Kalba"),
    "Ajman" to listOf("Ajman City"),
    "Ras Al Khaimah" to listOf("RAK City"),
    "Fujairah" to listOf("Fujairah City"),
    "Umm Al Quwain" to listOf("UAQ City"),
    "England" to listOf("London", "Manchester", "Birmingham", "Liverpool", "Leeds"),
    "Scotland" to listOf("Edinburgh", "Glasgow", "Aberdeen"),
    "Wales" to listOf("Cardiff", "Swansea"),
    "Northern Ireland" to listOf("Belfast", "Derry"),
    "California" to listOf("Los Angeles", "San Francisco", "San Diego", "San Jose", "Sacramento"),
    "New York" to listOf("New York City", "Buffalo", "Albany", "Rochester"),
    "Texas" to listOf("Houston", "Dallas", "Austin", "San Antonio", "Fort Worth"),
    "Florida" to listOf("Miami", "Orlando", "Tampa", "Jacksonville"),
    "Illinois" to listOf("Chicago", "Springfield", "Naperville"),
    "Worldwide" to listOf("Global / Online")
)

// ==========================================
// MATERIAL 3 THEME WITH SYSTEM TYPOGRAPHY
// ==========================================

class MainActivity : ComponentActivity() {
    private lateinit var dealRepository: DealRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        dealRepository = DealRepository(SaleAlertDatabase.getInstance(applicationContext))
        StaticDealsSyncWorker.enqueuePeriodic(applicationContext)
        StaticDealsSyncWorker.enqueueOnce(applicationContext)
        // AdMob is initialized only after the consent flow is integrated.
        // Do not start advertising before verifying consent requirements.
        FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(!BuildConfig.DEBUG)
        setContent {
            SaleAlertTheme {
                SaleAlertScreen(dealRepository)
            }
        }
    }
}

@Composable
fun SaleAlertTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) {
        darkColorScheme(
            primary = Color(0xFFEF4444),
            secondary = Color(0xFFF97316),
            tertiary = Color(0xFF16A34A),
            background = Color(0xFF0F172A),
            surface = Color(0xFF1E293B),
            onBackground = Color(0xFFF8FAFC),
            onSurface = Color(0xFFF8FAFC)
        )
    } else {
        lightColorScheme(
            primary = Color(0xFFEF4444),
            secondary = Color(0xFFF97316),
            tertiary = Color(0xFF16A34A),
            background = Color(0xFFF8FAFC),
            surface = Color(0xFFFFFFFF),
            onBackground = Color(0xFF111827),
            onSurface = Color(0xFF111827)
        )
    }

    val typography = Typography(
        displayLarge = TextStyle(fontFamily = FontFamily.Default),
        displayMedium = TextStyle(fontFamily = FontFamily.Default),
        displaySmall = TextStyle(fontFamily = FontFamily.Default),
        headlineLarge = TextStyle(fontFamily = FontFamily.Default),
        headlineMedium = TextStyle(fontFamily = FontFamily.Default),
        headlineSmall = TextStyle(fontFamily = FontFamily.Default),
        titleLarge = TextStyle(fontFamily = FontFamily.Default),
        titleMedium = TextStyle(fontFamily = FontFamily.Default),
        titleSmall = TextStyle(fontFamily = FontFamily.Default),
        bodyLarge = TextStyle(fontFamily = FontFamily.Default),
        bodyMedium = TextStyle(fontFamily = FontFamily.Default),
        bodySmall = TextStyle(fontFamily = FontFamily.Default),
        labelLarge = TextStyle(fontFamily = FontFamily.Default),
        labelMedium = TextStyle(fontFamily = FontFamily.Default),
        labelSmall = TextStyle(fontFamily = FontFamily.Default)
    )

    MaterialTheme(
        colorScheme = colorScheme,
        typography = typography,
        content = content
    )
}

fun getSavedDealIds(context: Context): Set<String> {
    val prefs = context.getSharedPreferences("sale_alert_saved_deals", Context.MODE_PRIVATE)
    return prefs.getStringSet("saved_ids", emptySet()) ?: emptySet()
}

fun saveDealBookmark(context: Context, dealId: String, save: Boolean, onUpdated: (Set<String>) -> Unit) {
    val prefs = context.getSharedPreferences("sale_alert_saved_deals", Context.MODE_PRIVATE)
    val current = prefs.getStringSet("saved_ids", mutableSetOf())?.toMutableSet() ?: mutableSetOf()
    if (save) current.add(dealId) else current.remove(dealId)
    prefs.edit().putStringSet("saved_ids", current).apply()
    onUpdated(current.toSet())
}

fun hasLocationPermission(context: Context): Boolean {
    return ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
           ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
}

// ==========================================
// MAIN SCREEN & REUSABLE COMPONENTS
// ==========================================

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun SaleAlertScreen(dealRepository: DealRepository) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var currentRoute by rememberSaveable { mutableStateOf("home") }
    val savedDealIds = remember { mutableStateOf(getSavedDealIds(context)) }

    // All active deals are observed; each screen applies its own filters.
    var selectedCategory by remember { mutableStateOf("All") }
    var currentCity by remember { mutableStateOf(context.getSharedPreferences("sale_alert_settings", Context.MODE_PRIVATE).getString("city", "Sialkot") ?: "Sialkot") }
    var searchQuery by remember { mutableStateOf("") }
    var sortOption by remember { mutableStateOf("Latest") }
    var isScanning by remember { mutableStateOf(false) }
    var showLocationDisclosure by remember { mutableStateOf(false) }
    var userLat by remember { mutableStateOf<Double?>(null) }
    var userLng by remember { mutableStateOf<Double?>(null) }

    val dealsState = remember { mutableStateListOf<Deal>() }
    val categories = listOf("All", "Food", "Clothes", "Shoes", "Electronics", "Grocery", "Cosmetics", "City Promotions")

    val userCountryCode = remember { getUserCountryCode(context) }

    LaunchedEffect(Unit) {
        delay(250)
        dealRepository.observeDeals(
            query = "",
            category = null,
            city = null,
            isBrand = null,
            limit = 100
        ).collect { deals ->
            dealsState.clear()
            dealsState.addAll(deals)
        }
    }

    fun fetchGpsLocation() {
        isScanning = true
        try {
            val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
                ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
            ) {
                fusedLocationClient.lastLocation.addOnSuccessListener { location ->
                    if (location != null) {
                        userLat = location.latitude
                        userLng = location.longitude
                        coroutineScope.launch(Dispatchers.IO) {
                            try {
                                val geocoder = Geocoder(context, Locale.getDefault())
                                @Suppress("DEPRECATION")
                                val addresses = geocoder.getFromLocation(location.latitude, location.longitude, 1)
                                if (!addresses.isNullOrEmpty()) {
                                    val city = addresses[0].locality ?: addresses[0].subAdminArea ?: "Sialkot"
                                    withContext(Dispatchers.Main) {
                                        currentCity = city
                                        isScanning = false
                                        Toast.makeText(context, "Location updated: $city", Toast.LENGTH_SHORT).show()
                                    }
                                } else {
                                    withContext(Dispatchers.Main) {
                                        isScanning = false
                                    }
                                }
                            } catch (_: Exception) {
                                withContext(Dispatchers.Main) {
                                    isScanning = false
                                }
                            }
                        }
                    } else {
                        isScanning = false
                        Toast.makeText(context, "GPS unavailable. Showing national deals.", Toast.LENGTH_SHORT).show()
                    }
                }.addOnFailureListener {
                    isScanning = false
                }
            } else {
                isScanning = false
            }
        } catch (_: Exception) {
            isScanning = false
        }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val fineGranted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] ?: false
        val coarseGranted = permissions[Manifest.permission.ACCESS_COARSE_LOCATION] ?: false
        if (fineGranted || coarseGranted) {
            fetchGpsLocation()
        }
    }

    if (showLocationDisclosure) {
        AlertDialog(
            onDismissRequest = { showLocationDisclosure = false },
            title = { Text("Location Permission", fontWeight = FontWeight.Bold) },
            text = { Text("Sale Alert uses your location to automatically display discounts, sales, and local shop offers available near you.") },
            confirmButton = {
                Button(
                    onClick = {
                        showLocationDisclosure = false
                        permissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.ACCESS_FINE_LOCATION,
                                Manifest.permission.ACCESS_COARSE_LOCATION
                            )
                        )
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text("Allow")
                }
            },
            dismissButton = {
                TextButton(onClick = { showLocationDisclosure = false }) {
                    Text("Not Now", color = Color.Gray)
                }
            }
        )
    }

    val currentTime = System.currentTimeMillis()
    val validDeals = dealsState.filter { (it.expiryTimestamp <= 0L || it.expiryTimestamp > currentTime) && it.status == "active" }
    // Never substitute a city center for the device's actual location.
    val activeUserLat = userLat
    val activeUserLng = userLng

    val filteredDeals = remember(selectedCategory, currentCity, searchQuery, sortOption, validDeals) {
        val tabFiltered = validDeals.filter { deal ->
            (searchQuery.isBlank() || deal.shopName.contains(searchQuery, ignoreCase = true) || deal.title.contains(searchQuery, ignoreCase = true) || deal.category.contains(searchQuery, ignoreCase = true)) &&
            (selectedCategory == "All" || selectedCategory == "City Promotions" || deal.category.equals(selectedCategory, ignoreCase = true))
        }

        when (sortOption) {
            "Highest Discount" -> tabFiltered.sortedByDescending { it.verifiedDiscountPercent ?: -1 }
            "Nearest" -> if (activeUserLat != null && activeUserLng != null) tabFiltered.sortedBy { deal ->
                if (hasValidCoordinates(deal.latitude, deal.longitude))
                    calculateDistanceKm(activeUserLat, activeUserLng, deal.latitude, deal.longitude)
                else Double.MAX_VALUE
            } else tabFiltered
            "Expiring Soon" -> tabFiltered.sortedBy { if (it.expiryTimestamp <= 0L) Long.MAX_VALUE else it.expiryTimestamp }
            else -> tabFiltered.sortedByDescending { it.verifiedAt ?: 0L } // Best available freshness signal; not a published-at timestamp
        }
    }

    val nearbyDeals = remember(validDeals, activeUserLat, activeUserLng) {
        if (activeUserLat == null || activeUserLng == null) emptyList()
        else validDeals.mapNotNull { deal ->
            if (deal.isBrand || !hasValidCoordinates(deal.latitude, deal.longitude)) return@mapNotNull null
            val distance = calculateDistanceKm(activeUserLat, activeUserLng, deal.latitude, deal.longitude)
            if (distance <= 30.0) deal.copy(distanceKm = distance) else null
        }.sortedBy { it.distanceKm }
    }

    Scaffold(
        bottomBar = {
            SaleAlertBottomNavBar(
                currentRoute = currentRoute,
                onRouteSelected = {
                    currentRoute = it
                    FirebaseAnalytics.getInstance(context).logEvent("screen_navigation", Bundle().apply {
                        putString("screen_name", it)
                    })
                }
            )
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(MaterialTheme.colorScheme.background)
        ) {
            when (currentRoute) {
                "home" -> HomeScreen(
                    deals = filteredDeals,
                    currentCity = currentCity,
                    savedDealIds = savedDealIds.value,
                    onToggleBookmark = { deal, save ->
                        saveDealBookmark(context, deal.id, save) { newSet ->
                            savedDealIds.value = newSet
                        }
                    },
                    onNavigateToDiscover = { currentRoute = "discover" }
                )
                "discover" -> DiscoverScreen(
                    deals = filteredDeals,
                    searchQuery = searchQuery,
                    onSearchQueryChange = { searchQuery = it },
                    selectedCategory = selectedCategory,
                    onCategorySelected = { selectedCategory = it },
                    sortOption = sortOption,
                    onSortSelected = { sortOption = it },
                    savedDealIds = savedDealIds.value,
                    onToggleBookmark = { deal, save ->
                        saveDealBookmark(context, deal.id, save) { newSet ->
                            savedDealIds.value = newSet
                        }
                    }
                )
                "nearby" -> NearbyScreen(
                    nearbyDeals = nearbyDeals,
                    hasLocationPermission = hasLocationPermission(context) && activeUserLat != null && activeUserLng != null,
                    onRequestPermission = {
                        permissionLauncher.launch(
                            arrayOf(
                                Manifest.permission.ACCESS_FINE_LOCATION,
                                Manifest.permission.ACCESS_COARSE_LOCATION
                            )
                        )
                    },
                    currentCity = currentCity,
                    savedDealIds = savedDealIds.value,
                    onToggleBookmark = { deal, save ->
                        saveDealBookmark(context, deal.id, save) { newSet ->
                            savedDealIds.value = newSet
                        }
                    }
                )
                "saved" -> SavedScreen(
                    savedDeals = validDeals.filter { it.id in savedDealIds.value },
                    savedDealIds = savedDealIds.value,
                    onToggleBookmark = { deal, save ->
                        saveDealBookmark(context, deal.id, save) { newSet ->
                            savedDealIds.value = newSet
                        }
                    }
                )
                "profile" -> ProfileScreen(
                    currentCity = currentCity,
                    onCitySelected = {
                        currentCity = it
                        context.getSharedPreferences("sale_alert_settings", Context.MODE_PRIVATE)
                            .edit().putString("city", it).apply()
                    }
                )
            }
        }
    }
}

// ==========================================
// REUSABLE COMPONENTS & DIALOGS
// ==========================================

// Flash Sale Countdown Timer Widget
@Composable
fun FlashSaleCountdownTimer(endTime: Long) {
    var timeLeft by remember { mutableStateOf(endTime - System.currentTimeMillis()) }

    LaunchedEffect(endTime) {
        while (true) {
            timeLeft = (endTime - System.currentTimeMillis()).coerceAtLeast(0L)
            delay(1000L)
        }
    }

    if (timeLeft <= 0) {
        Surface(
            color = Color(0xFFE0E0E0),
            shape = RoundedCornerShape(4.dp)
        ) {
            Text(
                text = "Deal Expired",
                color = Color.DarkGray,
                fontWeight = FontWeight.Bold,
                fontSize = 11.sp,
                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
            )
        }
        return
    }

    val hours = (timeLeft / (1000 * 60 * 60)) % 24
    val minutes = (timeLeft / (1000 * 60)) % 60
    val seconds = (timeLeft / 1000) % 60

    val timeString = String.format(Locale.getDefault(), "%02d:%02d:%02d remaining", hours, minutes, seconds)

    Surface(
        color = Color(0xFFFFEBEE),
        shape = RoundedCornerShape(6.dp),
        border = BorderStroke(1.dp, Color(0xFFE02424))
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Default.Info, contentDescription = null, tint = Color(0xFFE02424), modifier = Modifier.size(12.dp))
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "🔥 Flash Sale • $timeString",
                color = Color(0xFFE02424),
                fontWeight = FontWeight.Bold,
                fontSize = 11.sp
            )
        }
    }
}

// Deal Card with 16:9 Ratio Image Box decoding base64ToBitmap()
@Composable
fun DealCard(deal: Deal) {
    val context = LocalContext.current
    var showReportDialog by remember { mutableStateOf(false) }

    val sanitizedDealUrl = sanitizeUrl(deal.url)
    val isUrlValid = sanitizedDealUrl.isNotBlank() && isValidUrl(sanitizedDealUrl)

    val sdf = SimpleDateFormat("dd MMM yyyy", Locale.getDefault())
    val expiryStr = if (deal.expiryTimestamp > 0L) sdf.format(Date(deal.expiryTimestamp)) else null

    val decodedBitmap = rememberDecodedBitmap(deal.imageBase64)
    val brandDomain = extractDomain(deal.url, deal.shopName)
    val faviconBitmap = rememberFaviconBitmap(brandDomain)

    if (showReportDialog) {
        AlertDialog(
            onDismissRequest = { showReportDialog = false },
            title = { Text("Report Deal", fontWeight = FontWeight.Bold) },
            text = { Text("Report this deal for inappropriate content or expired status?") },
            confirmButton = {
                Button(
                    onClick = {
                        showReportDialog = false
                        Toast.makeText(context, "Deal reporting is not available yet.", Toast.LENGTH_LONG).show()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE02424))
                ) {
                    Text("Report")
                }
            },
            dismissButton = {
                TextButton(onClick = { showReportDialog = false }) {
                    Text("Cancel", color = Color.Gray)
                }
            }
        )
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            // 16:9 Ratio Image Box rendering decodedBitmap or Favicon logo
            if (decodedBitmap != null) {
                Image(
                    bitmap = decodedBitmap.asImageBitmap(),
                    contentDescription = "Deal Image",
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(160.dp)
                        .clip(RoundedCornerShape(12.dp))
                )
            } else if (faviconBitmap != null) {
                Surface(
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(110.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Image(
                                bitmap = faviconBitmap.asImageBitmap(),
                                contentDescription = "Brand Favicon",
                                modifier = Modifier
                                    .size(42.dp)
                                    .clip(RoundedCornerShape(8.dp))
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(deal.shopName, fontWeight = FontWeight.Bold, fontSize = 13.sp, color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            } else {
                Surface(
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(100.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(deal.shopName, fontWeight = FontWeight.Bold, fontSize = 14.sp, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }

            // Top Row: Brand / Shop Name & Prominent Discount Badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = deal.shopName,
                        fontWeight = FontWeight.Bold,
                        fontSize = 15.sp,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    deal.verifiedDiscountPercent?.let { discountPercent ->
                        Surface(
                            color = Color(0xFFE02424),
                            shape = RoundedCornerShape(6.dp)
                        ) {
                            Text(
                                text = "$discountPercent% OFF",
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                fontSize = 11.sp,
                                modifier = Modifier.padding(horizontal = 7.dp, vertical = 3.dp)
                            )
                        }
                    }
                    Spacer(modifier = Modifier.width(4.dp))
                    IconButton(
                        onClick = { showReportDialog = true },
                        modifier = Modifier.size(26.dp)
                    ) {
                        Icon(Icons.Default.MoreVert, contentDescription = "More", tint = Color.Gray, modifier = Modifier.size(15.dp))
                    }
                }
            }

            // Deal Title
            Text(
                text = deal.title,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f),
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )

            deal.verifiedDiscountPercent?.let {
                val salePrice = deal.salePrice
                val originalPrice = deal.originalPrice
                if (salePrice != null && originalPrice != null) {
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "${deal.currency.orEmpty()} ${"%.2f".format(Locale.getDefault(), salePrice)}",
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Bold
                        )
                        Text(
                            text = "${deal.currency.orEmpty()} ${"%.2f".format(Locale.getDefault(), originalPrice)}",
                            color = Color.Gray,
                            style = MaterialTheme.typography.bodySmall.copy(textDecoration = androidx.compose.ui.text.style.TextDecoration.LineThrough)
                        )
                    }
                }
            }

            if (deal.address.isNotBlank()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Place, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(12.dp))
                    Spacer(modifier = Modifier.width(3.dp))
                    Text(
                        text = if (!deal.isBrand && hasValidCoordinates(deal.latitude, deal.longitude)) {
                            "${deal.address} • ${"%.1f".format(Locale.getDefault(), deal.distanceKm)} km away"
                        } else {
                            deal.address
                        },
                        color = Color.Gray,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }
            }

            if (!deal.isBrand && deal.isFlashSale && deal.expiryTimestamp > 0L) {
                FlashSaleCountdownTimer(endTime = deal.expiryTimestamp)
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (deal.verifiedDiscountPercent != null) {
                        "${deal.category} • Verified"
                    } else {
                        "${deal.category} • Unverified listing"
                    },
                    color = Color.Gray,
                    fontSize = 11.sp
                )
                if (!deal.isBrand && expiryStr != null) {
                    Text(
                        text = "Expires: $expiryStr",
                        color = Color(0xFFE02424),
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(2.dp))

            // Action Buttons Row (National Brand Sales: Website only; Local Deals: Get Coupon, WhatsApp, Website)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                if (!deal.isBrand && deal.whatsappNumber.isNotBlank()) {
                    Button(
                        onClick = {
                            val rawNum = deal.whatsappNumber.replace(Regex("[^0-9]"), "")
                            val waNumber = when {
                                rawNum.startsWith("03") -> "92" + rawNum.substring(1)
                                rawNum.startsWith("92") -> rawNum
                                rawNum.startsWith("3") && rawNum.length == 10 -> "92$rawNum"
                                else -> ""
                            }
                            if (waNumber.isBlank()) return@Button
                            val message = "Hi, I want to claim this deal: '${deal.title}' at '${deal.shopName}' via Sale Alert app."
                            val whatsappUrl = "https://wa.me/$waNumber?text=${Uri.encode(message)}"
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(whatsappUrl))
                            try {
                                context.startActivity(intent)
                            } catch (_: Exception) {
                                Toast.makeText(context, "WhatsApp not installed", Toast.LENGTH_SHORT).show()
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF22C55E)),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1.1f),
                        contentPadding = PaddingValues(vertical = 4.dp)
                    ) {
                        Icon(Icons.Default.Info, contentDescription = null, modifier = Modifier.size(13.dp))
                        Spacer(modifier = Modifier.width(3.dp))
                        Text(text = "WhatsApp", fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                    }
                }

                // Visit Website / View Deal Button (National Brand Sales displays ONLY this button)
                OutlinedButton(
                    onClick = {
                        if (isUrlValid) {
                            try {
                                val customTabsIntent = CustomTabsIntent.Builder().build()
                                customTabsIntent.launchUrl(context, Uri.parse(sanitizedDealUrl))
                            } catch (_: ActivityNotFoundException) {
                                try {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(sanitizedDealUrl))
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Unable to open link", Toast.LENGTH_SHORT).show()
                                }
                            } catch (_: Exception) {
                                try {
                                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(sanitizedDealUrl))
                                    context.startActivity(intent)
                                } catch (_: Exception) {
                                    Toast.makeText(context, "Unable to open link", Toast.LENGTH_SHORT).show()
                                }
                            }
                        } else {
                            Toast.makeText(context, "Invalid website link", Toast.LENGTH_SHORT).show()
                        }
                    },
                    enabled = isUrlValid,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.weight(if (deal.isBrand) 1f else 0.9f),
                    contentPadding = PaddingValues(vertical = 4.dp)
                ) {
                    Text(text = if (deal.isBrand) "Visit Website" else "Website", fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                }
            }
        }
    }
}
