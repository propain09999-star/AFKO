package com.rdpcanary.app

import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.AdapterView
import android.widget.Spinner
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.rdpcanary.app.data.CanaryDatabase
import com.rdpcanary.app.ui.ResponseTimeChartView
import kotlinx.coroutines.launch

class ChartActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_chart)

        val db = CanaryDatabase.get(applicationContext)
        val spinner = findViewById<Spinner>(R.id.targetSpinner)
        val chart = findViewById<ResponseTimeChartView>(R.id.chartView)

        lifecycleScope.launch {
            val targets = db.dao().getTargetsOnce().map { it.target }
            if (targets.isEmpty()) {
                return@launch
            }

            val adapter = ArrayAdapter(this@ChartActivity, android.R.layout.simple_spinner_item, targets)
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            spinner.adapter = adapter

            suspend fun loadChartFor(target: String) {
                val recent = db.dao().getRecentForTarget(target, limit = 50).reversed()
                chart.setData(recent)
            }

            loadChartFor(targets.first())

            spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                    lifecycleScope.launch { loadChartFor(targets[position]) }
                }
                override fun onNothingSelected(parent: AdapterView<*>?) {}
            }
        }
    }
}
