package com.mfistudio.salealert.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface DealDao {
    @Query(
        """
        SELECT * FROM deals
        WHERE status = 'active'
          AND (expiryTime IS NULL OR expiryTime > :now)
          AND (startTime IS NULL OR startTime <= :now)
          AND (:category IS NULL OR categoryId = :category COLLATE NOCASE)
          AND (:city IS NULL OR cityId = :city COLLATE NOCASE OR cityId = 'All' COLLATE NOCASE)
          AND (
            :isBrand IS NULL OR
            (:isBrand = 1 AND sourceType != 'merchant') OR
            (:isBrand = 0 AND sourceType = 'merchant')
          )
          AND (
            :query = '' OR
            title LIKE '%' || :query || '%' COLLATE NOCASE OR
            shopName LIKE '%' || :query || '%' COLLATE NOCASE OR
            description LIKE '%' || :query || '%' COLLATE NOCASE
          )
        ORDER BY lastUpdated DESC
        LIMIT :limit OFFSET :offset
        """
    )
    fun observeDeals(
        now: Long,
        query: String,
        category: String?,
        city: String?,
        isBrand: Boolean?,
        limit: Int,
        offset: Int
    ): Flow<List<DealEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(deals: List<DealEntity>)

    @Query("DELETE FROM deals WHERE sourcePackId = :packId")
    suspend fun deletePack(packId: String)

    @Query("DELETE FROM deals WHERE expiryTime IS NOT NULL AND expiryTime <= :now")
    suspend fun deleteExpired(now: Long)
}

@Dao
interface SyncMetadataDao {
    @Query("SELECT value FROM sync_metadata WHERE `key` = :key")
    suspend fun getValue(key: String): String?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(metadata: SyncMetadataEntity)

    @Query("DELETE FROM sync_metadata WHERE `key` = :key")
    suspend fun delete(key: String)

    @Query("SELECT `key` FROM sync_metadata WHERE `key` LIKE 'pack:%'")
    suspend fun getPackKeys(): List<String>
}
