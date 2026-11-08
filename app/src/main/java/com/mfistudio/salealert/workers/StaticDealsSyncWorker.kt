package com.mfistudio.salealert.workers

import android.content.Context
import android.util.Log
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import androidx.room.withTransaction
import com.mfistudio.salealert.BuildConfig
import com.mfistudio.salealert.data.local.DealEntity
import com.mfistudio.salealert.data.local.SaleAlertDatabase
import com.mfistudio.salealert.data.local.SyncMetadataEntity
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.URI
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.time.Instant
import java.util.concurrent.TimeUnit
import java.util.zip.GZIPInputStream

private data class PackSpec(
    val id: String,
    val version: Long,
    val url: String,
    val sha256: String,
    val sizeBytes: Long
)

class StaticDealsSyncWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val baseUrl = BuildConfig.DEALS_CDN_BASE_URL.trim()
        if (baseUrl.isBlank()) {
            Log.w(TAG, "Deal sync is disabled: configure the public dealsCdnBaseUrl Gradle property.")
            return Result.failure(workDataOf("reason" to "CDN URL is not configured"))
        }

        return try {
            syncFrom(baseUrl)
            Result.success()
        } catch (error: IOException) {
            Log.e(TAG, "Deal feed download failed; cached deals were retained.", error)
            Result.retry()
        } catch (error: JSONException) {
            Log.e(TAG, "Deal feed contains invalid JSON; cached deals were retained.", error)
            Result.failure(workDataOf("reason" to "Invalid feed JSON"))
        } catch (error: IllegalArgumentException) {
            Log.e(TAG, "Deal feed validation failed; cached deals were retained.", error)
            Result.failure(workDataOf("reason" to (error.message ?: "Invalid feed")))
        }
    }

    private suspend fun syncFrom(baseUrl: String) {
        val baseUri = validateBaseUrl(baseUrl)
        val manifestUri = URI(baseUri.toString().trimEnd('/') + "/manifest.json")
        val db = SaleAlertDatabase.getInstance(applicationContext)
        val metadataDao = db.syncMetadataDao()
        val dealDao = db.dealDao()
        val manifestResponse = download(manifestUri.toString(), MAX_MANIFEST_BYTES)
        val manifest = JSONObject(String(manifestResponse, StandardCharsets.UTF_8))
        require(manifest.optInt("schemaVersion", -1) == SUPPORTED_SCHEMA) {
            "Unsupported manifest schema version"
        }
        val dataVersion = manifest.optLong("dataVersion", -1L)
        require(dataVersion >= 0L) { "Manifest dataVersion is invalid" }
        val packSpecs = parsePacks(manifest.optJSONArray("packs"))
        require(packSpecs.map { it.id }.distinct().size == packSpecs.size) {
            "Manifest contains duplicate pack IDs"
        }

        val changedPacks = packSpecs.filter { spec ->
            metadataDao.getValue(packKey(spec.id))?.toLongOrNull() != spec.version
        }
        val downloadedPacks = changedPacks.map { spec ->
            val packUri = resolvePackUri(baseUri, spec.url)
            val compressedBytes = download(packUri.toString(), MAX_PACK_BYTES)
            require(compressedBytes.size.toLong() == spec.sizeBytes) {
                "Pack ${spec.id} size does not match the manifest"
            }
            require(sha256(compressedBytes).equals(spec.sha256, ignoreCase = true)) {
                "Pack ${spec.id} checksum does not match the manifest"
            }
            spec to parseDealPack(spec, gunzip(compressedBytes))
        }

        db.withTransaction {
            dealDao.deleteExpired(System.currentTimeMillis())
            downloadedPacks.forEach { (spec, deals) ->
                dealDao.deletePack(spec.id)
                dealDao.upsertAll(deals)
                metadataDao.upsert(SyncMetadataEntity(packKey(spec.id), spec.version.toString()))
            }

            val currentPackIds = packSpecs.mapTo(mutableSetOf()) { it.id }
            metadataDao.getPackKeys().forEach { key ->
                val oldPackId = key.removePrefix(PACK_KEY_PREFIX)
                if (oldPackId !in currentPackIds) {
                    dealDao.deletePack(oldPackId)
                    metadataDao.delete(key)
                }
            }
            metadataDao.upsert(SyncMetadataEntity(MANIFEST_VERSION_KEY, dataVersion.toString()))
            manifest.optString("generatedAt").takeIf(String::isNotBlank)?.let { generatedAt ->
                metadataDao.upsert(SyncMetadataEntity(MANIFEST_GENERATED_AT_KEY, generatedAt))
            }
        }
        Log.i(TAG, "Deal feed sync committed: ${downloadedPacks.size} pack(s) updated.")
    }

    private fun parsePacks(array: JSONArray?): List<PackSpec> {
        require(array != null) { "Manifest has no packs array" }
        require(array.length() <= MAX_PACKS) { "Manifest contains too many packs" }
        return (0 until array.length()).map { index ->
            val item = array.getJSONObject(index)
            val id = item.optString("id")
            val version = item.optLong("version", -1L)
            val url = item.optString("url")
            val checksum = item.optString("sha256")
            val sizeBytes = item.optLong("sizeBytes", -1L)
            require(id.matches(PACK_ID_PATTERN)) { "Manifest contains an invalid pack ID" }
            require(version >= 0L) { "Pack $id has an invalid version" }
            require(checksum.matches(CHECKSUM_PATTERN)) { "Pack $id has an invalid SHA-256 checksum" }
            require(sizeBytes in 1..MAX_PACK_BYTES.toLong()) { "Pack $id has an invalid size" }
            require(url.isNotBlank()) { "Pack $id has no URL" }
            PackSpec(id, version, url, checksum, sizeBytes)
        }
    }

    private fun parseDealPack(spec: PackSpec, bytes: ByteArray): List<DealEntity> {
        val root = JSONObject(String(bytes, StandardCharsets.UTF_8))
        require(root.optInt("schemaVersion", -1) == SUPPORTED_SCHEMA) {
            "Pack ${spec.id} has an unsupported schema version"
        }
        val deals = root.optJSONArray("deals")
        require(deals != null && deals.length() <= MAX_DEALS_PER_PACK) {
            "Pack ${spec.id} has an invalid deals array"
        }
        val now = System.currentTimeMillis()
        val seenIds = mutableSetOf<String>()
        return (0 until deals.length()).mapNotNull { index ->
            val item = deals.getJSONObject(index)
            val dealId = item.optString("dealId").trim()
            val shopName = item.optString("merchant").trim()
            val title = item.optString("title").trim()
            val category = item.optString("categoryId").trim()
            val sourceType = item.optString("sourceType").trim()
            val status = item.optString("status", "active").trim()
            val expiryTime = item.optionalTimestamp("expiryTime")
            require(dealId.isNotBlank() && seenIds.add(dealId)) {
                "Pack ${spec.id} contains a missing or duplicate deal ID"
            }
            require(shopName.isNotBlank() && title.isNotBlank() && category.isNotBlank()) {
                "Pack ${spec.id} contains a deal missing required display fields"
            }
            require(sourceType in ALLOWED_SOURCE_TYPES) {
                "Pack ${spec.id} contains an unsupported source type"
            }
            require(status in ALLOWED_STATUSES) {
                "Pack ${spec.id} contains an unsupported deal status"
            }
            val originalPrice = item.optionalPrice("originalPrice")
            val salePrice = item.optionalPrice("salePrice")
            val verifiedAt = item.optionalTimestamp("verifiedAt")
            require((originalPrice == null) == (salePrice == null)) {
                "Deal $dealId must provide both prices or neither"
            }
            if (originalPrice != null && salePrice != null) {
                require(originalPrice > salePrice && salePrice > 0.0) {
                    "Deal $dealId has inconsistent prices"
                }
            }
            val currency = item.optNullableString("currency")
            if (originalPrice != null) {
                require(!currency.isNullOrBlank()) {
                    "Deal $dealId has prices but no currency"
                }
                try {
                    java.util.Currency.getInstance(currency)
                } catch (_: IllegalArgumentException) {
                    throw IllegalArgumentException("Deal $dealId has an invalid currency")
                }
            }
            if (expiryTime != null && expiryTime <= now) return@mapNotNull null

            DealEntity(
                dealId = dealId,
                merchantId = item.optNullableString("merchantId"),
                shopName = shopName,
                title = title,
                description = item.optNullableString("description"),
                address = item.optNullableString("address"),
                categoryId = category,
                cityId = item.optNullableString("cityId"),
                originalPrice = originalPrice,
                salePrice = salePrice,
                currency = currency,
                imageUrl = item.optNullableString("imageUrl"),
                sourceUrl = item.optNullableString("sourceUrl"),
                latitude = item.optionalCoordinate("latitude", -90.0, 90.0),
                longitude = item.optionalCoordinate("longitude", -180.0, 180.0),
                startTime = item.optionalTimestamp("startTime"),
                expiryTime = expiryTime,
                verifiedAt = verifiedAt,
                sourceType = sourceType,
                isSponsored = item.optBoolean("isSponsored", false),
                lastUpdated = item.optionalTimestamp("lastUpdated")
                    ?: throw IllegalArgumentException("Deal $dealId is missing lastUpdated"),
                status = status,
                sourcePackId = spec.id
            )
        }
    }

    private fun JSONObject.optionalPrice(key: String): Double? {
        if (!has(key) || isNull(key)) return null
        val value = optDouble(key, Double.NaN)
        require(value.isFinite() && value >= 0.0) { "Deal contains an invalid $key" }
        return value
    }

    private fun JSONObject.optionalCoordinate(key: String, min: Double, max: Double): Double? {
        if (!has(key) || isNull(key)) return null
        val value = optDouble(key, Double.NaN)
        require(value.isFinite() && value in min..max) { "Deal contains an invalid $key" }
        return value
    }

    private fun JSONObject.optionalTimestamp(key: String): Long? {
        if (!has(key) || isNull(key)) return null
        val value = get(key)
        val timestamp = when (value) {
            is Number -> value.toLong()
            is String -> try {
                Instant.parse(value).toEpochMilli()
            } catch (_: Exception) {
                throw IllegalArgumentException("Deal contains an invalid $key timestamp")
            }
            else -> throw IllegalArgumentException("Deal contains an invalid $key timestamp")
        }
        require(timestamp > 0L) { "Deal contains an invalid $key timestamp" }
        return timestamp
    }

    private fun JSONObject.optNullableString(key: String): String? {
        if (!has(key) || isNull(key)) return null
        return optString(key).trim().takeIf(String::isNotEmpty)
    }

    private fun validateBaseUrl(value: String): URI {
        val uri = try {
            URI(value)
        } catch (_: Exception) {
            throw IllegalArgumentException("Configured CDN URL is invalid")
        }
        require(
            uri.scheme.equals("https", ignoreCase = true) &&
                !uri.host.isNullOrBlank() &&
                uri.rawUserInfo == null &&
                uri.query == null &&
                uri.fragment == null
        ) { "Configured CDN URL must be an HTTPS origin or path" }
        return URI(uri.toString().trimEnd('/') + "/")
    }

    private fun resolvePackUri(baseUri: URI, relativeUrl: String): URI {
        require(!relativeUrl.startsWith('/') && !relativeUrl.contains('\\')) {
            "Pack URL must be relative to the configured CDN base"
        }
        val relativeUri = try {
            URI(relativeUrl)
        } catch (_: Exception) {
            throw IllegalArgumentException("Pack URL is invalid")
        }
        require(
            !relativeUri.isAbsolute &&
                relativeUri.rawAuthority == null &&
                relativeUri.rawQuery == null &&
                relativeUri.rawFragment == null &&
                relativeUri.path.split('/').none { it == ".." || it == "." }
        ) { "Pack URL must be a safe relative path" }
        val resolved = baseUri.resolve(relativeUri)
        require(
            resolved.scheme.equals("https", ignoreCase = true) &&
                resolved.host.equals(baseUri.host, ignoreCase = true) &&
                resolved.rawPath.startsWith(baseUri.rawPath)
        ) { "Pack URL must stay on the configured CDN host and path" }
        return resolved
    }

    private fun download(url: String, maxBytes: Int): ByteArray {
        val request = Request.Builder().url(url).get().build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("CDN returned HTTP ${response.code}")
            val body = response.body ?: throw IOException("CDN response has no body")
            if (body.contentLength() > maxBytes) throw IllegalArgumentException("CDN response exceeds size limit")
            body.byteStream().use { input ->
                ByteArrayOutputStream().use { output ->
                    val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                    var total = 0
                    while (true) {
                        ensureActive()
                        val count = input.read(buffer)
                        if (count < 0) break
                        total += count
                        if (total > maxBytes) throw IllegalArgumentException("CDN response exceeds size limit")
                        output.write(buffer, 0, count)
                    }
                    return output.toByteArray()
                }
            }
        }
    }

    private fun gunzip(compressed: ByteArray): ByteArray {
        GZIPInputStream(compressed.inputStream()).use { input ->
            ByteArrayOutputStream().use { output ->
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                var total = 0
                while (true) {
                    ensureActive()
                    val count = input.read(buffer)
                    if (count < 0) break
                    total += count
                    require(total <= MAX_UNCOMPRESSED_PACK_BYTES) {
                        "Uncompressed deal pack exceeds size limit"
                    }
                    output.write(buffer, 0, count)
                }
                return output.toByteArray()
            }
        }
    }

    private fun sha256(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }

    private fun packKey(packId: String) = PACK_KEY_PREFIX + packId

    private fun ensureActive() {
        if (isStopped) throw IOException("Deal feed sync was cancelled")
    }

    companion object {
        private const val TAG = "DealsSyncWorker"
        private const val SUPPORTED_SCHEMA = 1
        private const val MAX_PACKS = 100
        private const val MAX_DEALS_PER_PACK = 5_000
        private const val MAX_MANIFEST_BYTES = 256 * 1024
        private const val MAX_PACK_BYTES = 20 * 1024 * 1024
        private const val MAX_UNCOMPRESSED_PACK_BYTES = 30 * 1024 * 1024
        private const val MANIFEST_VERSION_KEY = "manifest:dataVersion"
        private const val MANIFEST_GENERATED_AT_KEY = "manifest:generatedAt"
        private const val PACK_KEY_PREFIX = "pack:"
        private val PACK_ID_PATTERN = Regex("[A-Za-z0-9._-]{1,80}")
        private val CHECKSUM_PATTERN = Regex("[A-Fa-f0-9]{64}")
        private val ALLOWED_SOURCE_TYPES = setOf("merchant", "brand", "publisher", "affiliate")
        private val ALLOWED_STATUSES = setOf("active", "pending", "rejected", "expired")
        private val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .callTimeout(45, TimeUnit.SECONDS)
            .build()

        fun enqueuePeriodic(context: Context): Boolean {
            if (BuildConfig.DEALS_CDN_BASE_URL.isBlank()) {
                Log.w(TAG, "Periodic sync was not scheduled: public deals CDN is not configured.")
                return false
            }
            val request = PeriodicWorkRequestBuilder<StaticDealsSyncWorker>(7, TimeUnit.DAYS)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES)
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODIC_WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                request
            )
            return true
        }

        fun enqueueOnce(context: Context): Boolean {
            if (BuildConfig.DEALS_CDN_BASE_URL.isBlank()) return false
            // First launch fetches the central feed. Later launches are capped at
            // one scheduled refresh per 7 days; no per-user Google API searches.
            val prefs = context.getSharedPreferences("sale_alert_feed_schedule", Context.MODE_PRIVATE)
            val now = System.currentTimeMillis()
            val lastScheduled = prefs.getLong("last_scheduled_at", 0L)
            if (lastScheduled > 0L && now >= lastScheduled &&
                now - lastScheduled < TimeUnit.DAYS.toMillis(7)) return false
            val request = OneTimeWorkRequestBuilder<StaticDealsSyncWorker>()
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.MINUTES)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                ONE_TIME_WORK_NAME,
                ExistingWorkPolicy.KEEP,
                request
            )
            prefs.edit().putLong("last_scheduled_at", now).apply()
            return true
        }

        private const val PERIODIC_WORK_NAME = "static-deals-periodic-sync"
        private const val ONE_TIME_WORK_NAME = "static-deals-manual-sync"
    }
}
