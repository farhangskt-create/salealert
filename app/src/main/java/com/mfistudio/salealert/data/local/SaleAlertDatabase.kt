package com.mfistudio.salealert.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [DealEntity::class, SyncMetadataEntity::class],
    version = 1,
    exportSchema = false
)
abstract class SaleAlertDatabase : RoomDatabase() {
    abstract fun dealDao(): DealDao
    abstract fun syncMetadataDao(): SyncMetadataDao

    companion object {
        @Volatile
        private var instance: SaleAlertDatabase? = null

        fun getInstance(context: Context): SaleAlertDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext,
                    SaleAlertDatabase::class.java,
                    "sale_alert_local.db"
                ).build().also { instance = it }
            }
    }
}
