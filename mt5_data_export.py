"""
mt5_data_export.py

Pulls historical OHLC data directly from a running MetaTrader 5 terminal
via its Python API, and converts it into the Candle format the backtest
engine expects (or saves it as CSV for data_loader.py).

REQUIREMENTS:
- Must run on Windows (or Linux/Mac via Wine) with the MetaTrader 5
  desktop terminal installed and logged into ANY account - this script
  only reads market data, it never places orders, so account type
  (demo or real) doesn't matter here.
- pip install MetaTrader5

This does NOT run on Android/Termux - the MetaTrader5 Python package
requires the actual MT5 terminal application, which is Windows-only.
Run this on whatever machine has MT5 installed.
"""

from __future__ import annotations
import csv
import sys
from datetime import datetime
from pathlib import Path

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package not installed, or not running on a")
    print("platform where it's supported (Windows, or Linux/Mac via Wine).")
    print("Install with: pip install MetaTrader5")
    sys.exit(1)


def export_history_to_csv(
    symbol: str,
    timeframe: int,
    date_from: datetime,
    date_to: datetime,
    output_path: str | Path,
) -> int:
    """
    Pulls historical rates for `symbol` between date_from/date_to and
    writes them to a CSV in the format data_loader.py expects.
    Returns the number of candles written.

    timeframe: use mt5.TIMEFRAME_* constants, e.g. mt5.TIMEFRAME_H1,
    mt5.TIMEFRAME_M15, mt5.TIMEFRAME_D1.
    """
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    try:
        rates = mt5.copy_rates_range(symbol, timeframe, date_from, date_to)
        if rates is None or len(rates) == 0:
            raise RuntimeError(
                f"No data returned for {symbol}. Check the symbol name matches "
                f"exactly what's in your MT5 Market Watch, and that the date "
                f"range has data available."
            )

        output_path = Path(output_path)
        with output_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "open", "high", "low", "close"])
            for rate in rates:
                ts = datetime.fromtimestamp(rate["time"])
                writer.writerow([
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    rate["open"],
                    rate["high"],
                    rate["low"],
                    rate["close"],
                ])

        return len(rates)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python mt5_data_export.py <symbol> <timeframe> <from_date> <to_date>")
        print("Example: python mt5_data_export.py EURUSD H1 2025-01-01 2026-01-01")
        print("Timeframes: M1, M5, M15, M30, H1, H4, D1, W1, MN1")
        sys.exit(1)

    symbol = sys.argv[1]
    tf_name = sys.argv[2].upper()
    date_from = datetime.strptime(sys.argv[3], "%Y-%m-%d")
    date_to = datetime.strptime(sys.argv[4], "%Y-%m-%d")

    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    if tf_name not in tf_map:
        print(f"Unknown timeframe {tf_name}. Choose from: {', '.join(tf_map)}")
        sys.exit(1)

    output_file = f"{symbol}_{tf_name}.csv"
    count = export_history_to_csv(symbol, tf_map[tf_name], date_from, date_to, output_file)
    print(f"Wrote {count} candles to {output_file}")
    print(f"Load it with: python data_loader.py {output_file} {symbol}")
              
