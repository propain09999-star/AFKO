package com.rdpcanary.app.work

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.rdpcanary.app.data.CanaryDatabase
import com.rdpcanary.app.data.CanaryResult
import java.net.InetSocketAddress
import java.net.Socket

/**
 * Runs on a WorkManager schedule (default: every 15 minutes, the OS minimum for
 * periodic work). For every saved target, opens a raw TCP socket to host:port and
 * times the connect. This is a "canary" check, not a full RDP protocol login -
 * see README for why, and how to keep a full-login PowerShell monitor as well.
 */
class RdpCanaryWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    companion object {
        const val CHANNEL_ID = "rdp_canary_alerts"
        const val CONNECT_TIMEOUT_MS = 5000
    }

    override suspend fun doWork(): Result {
        val db = CanaryDatabase.get(applicationContext)
        val targets = db.dao().getTargetsOnce()

        for (t in targets) {
            val (host, port) = parseTarget(t.target)
            val (success, elapsedMs, error) = checkTcp(host, port)

            db.dao().insertResult(
                CanaryResult(
                    timestampMs = System.currentTimeMillis(),
                    target = t.target,
                    success = success,
                    responseTimeMs = elapsedMs,
                    error = error
                )
            )

            if (!success) {
                notifyFailure(t.target, error)
            }
        }
        return Result.success()
    }

    private fun parseTarget(raw: String): Pair<String, Int> {
        val parts = raw.split(":")
        return if (parts.size == 2) {
            parts[0] to (parts[1].toIntOrNull() ?: 3389)
        } else {
            raw to 3389
        }
    }

    /** Returns (success, elapsedMs, errorMessageOrNull). */
    private fun checkTcp(host: String, port: Int): Triple<Boolean, Long, String?> {
        val start = System.currentTimeMillis()
        return try {
            Socket().use { socket ->
                socket.connect(InetSocketAddress(host, port), CONNECT_TIMEOUT_MS)
            }
            Triple(true, System.currentTimeMillis() - start, null)
        } catch (e: Exception) {
            Triple(false, System.currentTimeMillis() - start, e.message ?: e.javaClass.simpleName)
        }
    }

    private fun notifyFailure(target: String, error: String?) {
        val nm = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, "RDP Canary Alerts", NotificationManager.IMPORTANCE_HIGH
            )
            nm.createNotificationChannel(channel)
        }
        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_error)
            .setContentTitle("RDP Canary: $target unreachable")
            .setContentText(error ?: "Connection failed")
            .setAutoCancel(true)
            .build()
        nm.notify(target.hashCode(), notification)
    }
}
