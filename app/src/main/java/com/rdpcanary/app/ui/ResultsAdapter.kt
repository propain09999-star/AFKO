package com.rdpcanary.app.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.rdpcanary.app.R
import com.rdpcanary.app.data.CanaryResult
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class ResultsAdapter : RecyclerView.Adapter<ResultsAdapter.ViewHolder>() {

    private var items: List<CanaryResult> = emptyList()
    private val dateFmt = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())

    fun submitList(newItems: List<CanaryResult>) {
        items = newItems
        notifyDataSetChanged()
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val targetText: TextView = view.findViewById(R.id.targetText)
        val statusText: TextView = view.findViewById(R.id.statusText)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_result, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        holder.targetText.text = item.target
        val statusWord = if (item.success) "UP" else "DOWN"
        val time = dateFmt.format(Date(item.timestampMs))
        holder.statusText.text = if (item.success) {
            "$statusWord  •  $time  •  ${item.responseTimeMs} ms"
        } else {
            "$statusWord  •  $time  •  ${item.error ?: "unknown error"}"
        }
    }

    override fun getItemCount(): Int = items.size
}
