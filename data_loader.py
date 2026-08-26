"""
data_loader.py

Loads historical OHLC data from CSV into the Candle format the backtest
engine expects. Supports the column layout most brokers/data providers
export (timestamp, open, high, low, close), with a bit of flexibility
for common column name variations.

Does not fetch anything over the network - point it at a CSV file you
already have (exported from your broker, MetaTrader, Dukascopy, a
market data vendor, etc).
"""

from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path

from backtest_engine import Candle

# Common column name variants seen across different data providers
TIMESTAMP_KEYS = ["timestamp", "time", "date", "datetime"]
OPEN_KEYS = ["open", "o"]
HIGH_KEYS = ["high", "h"]
LOW_KEYS = ["low", "l"]
CLOSE_KEYS = ["close", "c"]

# Try these formats in order until one parses successfully
TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
]


def _find_key(row_keys: list[str], candidates: list[str]) -> str:
    lowered = {k.lower().strip(): k for k in row_keys}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    raise ValueError(
        f"Could not find a column matching any of {candidates} in header {row_keys}"
    )


def _parse_timestamp(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    # Last resort: try epoch seconds/millis
    try:
        num = float(raw)
        if num > 1e12:  # looks like milliseconds
            num /= 1000
        return datetime.fromtimestamp(num)
    except ValueError:
        raise ValueError(f"Could not parse timestamp: {raw!r}")


def load_candles_from_csv(path: str | Path, symbol: str) -> list[Candle]:
    """
    Reads a CSV of historical OHLC data and returns a chronologically
    sorted list of Candle objects for the given symbol.

    The CSV must have a header row. Column names are matched
    case-insensitively against common variants (see *_KEYS above).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")

    candles: list[Candle] = []
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")

        ts_key = _find_key(reader.fieldnames, TIMESTAMP_KEYS)
        open_key = _find_key(reader.fieldnames, OPEN_KEYS)
        high_key = _find_key(reader.fieldnames, HIGH_KEYS)
        low_key = _find_key(reader.fieldnames, LOW_KEYS)
        close_key = _find_key(reader.fieldnames, CLOSE_KEYS)

        for row in reader:
            try:
                candles.append(
                    Candle(
                        timestamp=_parse_timestamp(row[ts_key]),
                        symbol=symbol,
                        open=float(row[open_key]),
                        high=float(row[high_key]),
                        low=float(row[low_key]),
                        close=float(row[close_key]),
                    )
                )
            except (ValueError, KeyError) as e:
                # Skip malformed rows rather than crashing the whole load -
                # real-world exports often have a stray blank line or two
                continue

    candles.sort(key=lambda c: c.timestamp)

    if not candles:
        raise ValueError(f"No valid candles parsed from {path}")

    return candles


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python data_loader.py <path_to_csv> <symbol>")
        print("Example: python data_loader.py EURUSD_H1.csv EURUSD")
        sys.exit(1)

    candles = load_candles_from_csv(sys.argv[1], sys.argv[2])
    print(f"Loaded {len(candles)} candles for {sys.argv[2]}")
    print(f"Range: {candles[0].timestamp} to {candles[-1].timestamp}")
    print(f"First candle: {candles[0]}")
    print(f"Last candle:  {candles[-1]}")
