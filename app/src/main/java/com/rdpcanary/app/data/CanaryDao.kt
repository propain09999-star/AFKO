package com.rdpcanary.app.data

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface CanaryDao {

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun addTarget(target: MonitorTarget)

    @Delete
    suspend fun removeTarget(target: MonitorTarget)

    @Query("SELECT * FROM targets ORDER BY addedAtMs ASC")
    fun observeTargets(): Flow<List<MonitorTarget>>

    @Query("SELECT * FROM targets ORDER BY addedAtMs ASC")
    suspend fun getTargetsOnce(): List<MonitorTarget>

    @Insert
    suspend fun insertResult(result: CanaryResult)

    @Query("SELECT * FROM canary_results ORDER BY timestampMs DESC LIMIT 500")
    fun observeRecentResults(): Flow<List<CanaryResult>>

    @Query("SELECT * FROM canary_results ORDER BY timestampMs ASC")
    suspend fun getAllResultsForExport(): List<CanaryResult>

    @Query("""
        SELECT * FROM canary_results
        WHERE target = :target
        ORDER BY timestampMs DESC LIMIT :limit
    """)
    suspend fun getRecentForTarget(target: String, limit: Int = 50): List<CanaryResult>

    @Query("""
        SELECT * FROM canary_results
        WHERE target = :target
        ORDER BY timestampMs DESC LIMIT 1
    """)
    suspend fun getLatestForTarget(target: String): CanaryResult?
}
