"""
strategy_sma_crossover.py

A real (if simple) strategy: buy when the fast SMA crosses above the slow
SMA, sell/close when it crosses back below. This is a well-known, widely
documented approach (not proprietary alpha) - a solid, honest baseline to
extend, not something to expect edge from as-is. Real strategies usually
need more: volatility filters, session timing, multiple confirming
signals, walk-forward validation across different market regimes, etc.

Plugs directly into BacktestEngine's strategy callable signature:
    (history: list[Candle]) -> OrderParams | None
"""

from __future__ import annotations
from typing import Optional

from backtest_engine import Candle
from orchestration_schema import OrderParams


def _sma(values: list[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


class SmaCrossoverStrategy:
    """
    Stateful wrapper (needs to remember whether it's currently long, since
    the crossover is a signal to open OR close depending on current state)
    around a plain function, so it can be passed directly as the strategy
    callable to BacktestEngine.
    """

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        vol_lots: float = 0.1,
        sl_pips: float = 40,
        tp_pips: float = 80,
        max_account_risk_pct: float = 0.5,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.vol_lots = vol_lots
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.max_account_risk_pct = max_account_risk_pct
        self._currently_long = False

    def __call__(self, history: list[Candle]) -> Optional[OrderParams]:
        if len(history) < self.slow_period + 1:
            return None

        closes = [c.close for c in history]

        fast_now = _sma(closes, self.fast_period)
        slow_now = _sma(closes, self.slow_period)
        fast_prev = _sma(closes[:-1], self.fast_period)
        slow_prev = _sma(closes[:-1], self.slow_period)

        if None in (fast_now, slow_now, fast_prev, slow_prev):
            return None

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now

        symbol = history[-1].symbol

        if crossed_up and not self._currently_long:
            self._currently_long = True
            return OrderParams(
                strategy_name="sma_crossover",
                action="buy",
                symbol=symbol,
                vol_lots=self.vol_lots,
                sl_pips=self.sl_pips,
                tp_pips=self.tp_pips,
                max_account_risk_pct=self.max_account_risk_pct,
                dry_run=False,
                notes=f"fast={fast_now:.5f} slow={slow_now:.5f} crossed up",
            )

        if crossed_down and self._currently_long:
            self._currently_long = False
            # Note: BacktestEngine's simplified position model auto-closes
            # on SL/TP only. A crossover-down exit signal here is informational
            # for now - see the "known limitations" note in the README about
            # wiring explicit signal-based exits into the engine.

        return None


if __name__ == "__main__":
    # Quick smoke test against the same synthetic data style as
    # backtest_engine.py's self-test, so this file is runnable standalone.
    import random
    from datetime import datetime, timedelta
    from backtest_engine import BacktestEngine

    random.seed(7)
    candles: list[Candle] = []
    price = 1.1000
    start = datetime(2026, 1, 1)
    for i in range(2000):
        change = random.uniform(-0.0012, 0.0012)
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + random.uniform(0, 0.0004)
        low_p = min(open_p, close_p) - random.uniform(0, 0.0004)
        candles.append(Candle(start + timedelta(hours=i), "EURUSD", open_p, high_p, low_p, close_p))
        price = close_p

    strategy = SmaCrossoverStrategy(fast_period=10, slow_period=30)
    engine = BacktestEngine(candles, strategy, starting_balance=10_000.0)
    result = engine.run()
    print(result.summary())
