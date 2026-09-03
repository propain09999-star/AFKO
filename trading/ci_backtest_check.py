"""
ci_backtest_check.py

Run in CI on every push/PR that touches strategy or engine code. Runs the
strategy against a fixed synthetic dataset (deterministic seed, so results
are reproducible run-to-run) and fails the build if performance falls
below thresholds you define.

This catches regressions - e.g. someone tweaks the SMA periods and
accidentally turns a profitable-ish strategy into a losing one, or a
schema change breaks order validation silently. It does NOT tell you a
strategy is good; a strategy passing these thresholds on synthetic data
says nothing about real market performance. This is a regression guard,
not a profitability guarantee.

Swap in real historical data (via data_loader.py) once you have it, and
tighten/adjust the thresholds to match what you actually expect from your
strategy - the numbers below are placeholders.
"""

import random
import sys
from datetime import datetime, timedelta

from backtest_engine import BacktestEngine, Candle
from strategy_sma_crossover import SmaCrossoverStrategy

# --- Fixed thresholds - adjust these to match your actual expectations ---
MAX_ACCEPTABLE_DRAWDOWN_PCT = (
    25.0  # fail if drawdown exceeds this % of starting balance
)
MIN_ACCEPTABLE_WIN_RATE = 0.0  # set a real floor once you have real data
REQUIRE_NO_CRASH = True  # the engine must run start-to-finish without exceptions


def generate_fixed_dataset(seed: int = 42, num_candles: int = 2000) -> list[Candle]:
    """Deterministic synthetic data - same seed means same output every CI run,
    so a threshold failure means something actually changed in the code,
    not that the random data happened to be different this time."""
    random.seed(seed)
    candles: list[Candle] = []
    price = 1.1000
    start = datetime(2026, 1, 1)
    for i in range(num_candles):
        change = random.uniform(-0.0012, 0.0012)
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + random.uniform(0, 0.0004)
        low_p = min(open_p, close_p) - random.uniform(0, 0.0004)
        candles.append(
            Candle(start + timedelta(hours=i), "EURUSD", open_p, high_p, low_p, close_p)
        )
        price = close_p
    return candles


def main() -> int:
    report_lines = []
    exit_code = 0

    try:
        candles = generate_fixed_dataset()
        strategy = SmaCrossoverStrategy(fast_period=10, slow_period=30)
        engine = BacktestEngine(candles, strategy, starting_balance=10_000.0)
        result = engine.run()
    except Exception as e:
        report_lines.append(f"CRASH: backtest raised an exception: {e}")
        report_lines.append("This is an automatic failure regardless of thresholds.")
        _write_report(report_lines)
        print("\n".join(report_lines))
        return 1

    report_lines.append(result.summary())
    report_lines.append("")

    drawdown_pct = (result.max_drawdown / result.starting_balance) * 100
    report_lines.append(
        f"Drawdown %: {drawdown_pct:.2f}% (limit: {MAX_ACCEPTABLE_DRAWDOWN_PCT}%)"
    )

    if drawdown_pct > MAX_ACCEPTABLE_DRAWDOWN_PCT:
        report_lines.append(
            f"FAIL: drawdown {drawdown_pct:.2f}% exceeds limit {MAX_ACCEPTABLE_DRAWDOWN_PCT}%"
        )
        exit_code = 1

    if result.win_rate < MIN_ACCEPTABLE_WIN_RATE:
        report_lines.append(
            f"FAIL: win rate {result.win_rate:.1%} below minimum {MIN_ACCEPTABLE_WIN_RATE:.1%}"
        )
        exit_code = 1

    if exit_code == 0:
        report_lines.append("PASS: all thresholds met")

    _write_report(report_lines)
    print("\n".join(report_lines))
    return exit_code


def _write_report(lines: list[str]) -> None:
    with open("backtest_report.txt", "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
