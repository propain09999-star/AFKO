package com.rdpcanary.app

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.rdpcanary.app.data.CanaryDatabase
import com.rdpcanary.app.data.MonitorTarget
import com.rdpcanary.app.ui.ResultsAdapter
import com.rdpcanary.app.work.RdpCanaryWorker
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileWriter
import java.util.concurrent.TimeUnit

class MainActivity : AppCompatActivity() {

    private val adapter = ResultsAdapter()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val db = CanaryDatabase.get(applicationContext)

        val targetInput = findViewById<EditText>(R.id.targetInput)
        val addButton = findViewById<Button>(R.id.addButton)
        val exportButton = findViewById<Button>(R.id.exportButton)
        val resultsList = findViewById<RecyclerView>(R.id.resultsList)

        resultsList.layoutManager = LinearLayoutManager(this)
        resultsList.adapter = adapter

        lifecycleScope.launch {
            db.dao().observeRecentResults().collect { results ->
                adapter.submitList(results)
            }
        }

        addButton.setOnClickListener {
            val raw = targetInput.text.toString().trim()
            if (raw.isNotEmpty()) {
                lifecycleScope.launch {
                    db.dao().addTarget(MonitorTarget(target = raw, addedAtMs = System.currentTimeMillis()))
                }
                targetInput.text.clear()
            }
        }

        exportButton.setOnClickListener {
            lifecycleScope.launch {
                exportAndShareCsv()
            }
        }

        findViewById<Button>(R.id.chartButton).setOnClickListener {
            startActivity(Intent(this, ChartActivity::class.java))
        }

        schedulePeriodicChecks()
    }

    private fun schedulePeriodicChecks() {
        val request = PeriodicWorkRequestBuilder<RdpCanaryWorker>(15, TimeUnit.MINUTES).build()
        WorkManager.getInstance(applicationContext).enqueueUniquePeriodicWork(
            "rdp_canary_periodic_check",
            ExistingPeriodicWorkPolicy.KEEP,
            request
        )
    }

    private suspend fun exportAndShareCsv() {
        val db = CanaryDatabase.get(applicationContext)
        val rows = db.dao().getAllResultsForExport()

        val file = File(cacheDir, "rdp_canary_log.csv")
        FileWriter(file).use { writer ->
            writer.append("Timestamp,Target,Status,ResponseTimeMS,Error\n")
            for (r in rows) {
                val status = if (r.success) "Success" else "Failed"
                writer.append("${r.timestampMs},${r.target},$status,${r.responseTimeMs},${r.error ?: "None"}\n")
            }
        }

        val uri = FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = "text/csv"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(shareIntent, "Share RDP Canary log"))
    }
}
