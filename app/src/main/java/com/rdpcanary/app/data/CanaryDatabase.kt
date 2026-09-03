package com.rdpcanary.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [CanaryResult::class, MonitorTarget::class],
    version = 1,
    exportSchema = false
)
abstract class CanaryDatabase : RoomDatabase() {
    abstract fun dao(): CanaryDao

    companion object {
        @Volatile private var INSTANCE: CanaryDatabase? = null

        fun get(context: Context): CanaryDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    CanaryDatabase::class.java,
                    "rdp_canary.db"
                ).build().also { INSTANCE = it }
            }
    }
}
