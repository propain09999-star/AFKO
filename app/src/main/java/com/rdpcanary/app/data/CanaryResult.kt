package com.rdpcanary.app.data

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * One row = one TCP canary check against a target host:port.
 */
@Entity(tableName = "canary_results")
data class CanaryResult(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestampMs: Long,
    val target: String,        // "host:port"
    val success: Boolean,
    val responseTimeMs: Long,
    val error: String?
)

/**
 * A monitored target the user added (host:port pair).
 */
@Entity(tableName = "targets")
data class MonitorTarget(
    @PrimaryKey val target: String, // "host:port", also acts as unique key
    val addedAtMs: Long
)
