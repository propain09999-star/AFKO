package com.rdpcanary.app.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import com.rdpcanary.app.data.CanaryResult

class ResponseTimeChartView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    private var points: List<CanaryResult> = emptyList()

    private val linePaint = Paint().apply {
        color = Color.parseColor("#4CAF50")
        strokeWidth = 4f
        style = Paint.Style.STROKE
        isAntiAlias = true
    }
    private val failPaint = Paint().apply {
        color = Color.parseColor("#F44336")
        style = Paint.Style.FILL
        isAntiAlias = true
    }
    private val axisPaint = Paint().apply {
        color = Color.parseColor("#555555")
        strokeWidth = 2f
    }
    private val textPaint = Paint().apply {
        color = Color.parseColor("#AAAAAA")
        textSize = 24f
        isAntiAlias = true
    }

    fun setData(results: List<CanaryResult>) {
        points = results
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (points.isEmpty()) {
            canvas.drawText("No data yet", 20f, height / 2f, textPaint)
            return
        }

        val paddingLeft = 80f
        val paddingBottom = 40f
        val paddingTop = 20f
        val chartWidth = width - paddingLeft - 20f
        val chartHeight = height - paddingBottom - paddingTop

        val successResults = points.filter { it.success }
        val maxMs = (successResults.maxOfOrNull { it.responseTimeMs } ?: 100L).coerceAtLeast(1L)

        canvas.drawLine(paddingLeft, paddingTop, paddingLeft, height - paddingBottom, axisPaint)
        canvas.drawLine(paddingLeft, height - paddingBottom, width.toFloat(), height - paddingBottom, axisPaint)
        canvas.drawText("${maxMs}ms", 4f, paddingTop + 20f, textPaint)
        canvas.drawText("0", 4f, height - paddingBottom, textPaint)

        val stepX = if (points.size > 1) chartWidth / (points.size - 1) else 0f
        var prevX = 0f
        var prevY = 0f
        var havePrev = false

        points.forEachIndexed { i, result ->
            val x = paddingLeft + stepX * i
            if (!result.success) {
                val y = height - paddingBottom
                canvas.drawCircle(x, y, 10f, failPaint)
                havePrev = false
                return@forEachIndexed
            }

            val ratio = result.responseTimeMs.toFloat() / maxMs.toFloat()
            val y = (height - paddingBottom) - (ratio * chartHeight)

            if (havePrev) {
                canvas.drawLine(prevX, prevY, x, y, linePaint)
            }
            prevX = x
            prevY = y
            havePrev = true
        }
    }
}
