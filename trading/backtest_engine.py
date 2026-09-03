"""
backtest_engine.py

Pure historical simulation. No exchange/broker connection of any kind -
this only replays past price data against your strategy logic and reports
what would have happened. That's intentional: this is step 2 of the
sequence (schema -> backtest -> paper trading -> small real capital),
and nothing here should be wired to a live API.

Usage pattern:
    1. Load historical OHLC data into a list of Candle
    2. Write a strategy function: (history: list[Candle]) -> OrderParams | None
    3. Run BacktestEngine(candles, strategy, starting_balance).run()
    4. Inspect the returned BacktestResult for P&L, win rate, drawdown

Every order the strategy produces is validated through OrderParams (see
orchestration_schema.py) before the engine will act on it - a strategy
that returns something outside that schema's rules gets rejected, not
silently coerced.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from orchestration_schema import Action, OrderParams


@dataclass
class Candle:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class Position:
    symbol: str
    action: Action
    entry_price: float
    vol_lots: float
    sl_price: float
    tp_price: float
    opened_at: datetime
    trace_id: str


@dataclass
class ClosedTrade:
    symbol: str
    action: Action
    entry_price: float
    exit_price: float
    vol_lots: float
    opened_at: datetime
    closed_at: datetime
    pnl: float
    exit_reason: str  # "sl", "tp", "end_of_data"


@dataclass
class BacktestResult:
    starting_balance: float
    ending_balance: float
    trades: list[ClosedTrade] = field(default_factory=list)

    @property
    def total_pnl(self) -> float:
        return self.ending_balance - self.starting_balance

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl > 0)
        return wins / len(self.trades)

    @property
    def max_drawdown(self) -> float:
        """Largest peak-to-trough drop in running balance, in currency units."""
        running = self.starting_balance
        peak = running
        max_dd = 0.0
        for t in self.trades:
            running += t.pnl
            peak = max(peak, running)
            max_dd = max(max_dd, peak - running)
        return max_dd

    def summary(self) -> str:
        lines = [
            f"Starting balance: {self.starting_balance:.2f}",
            f"Ending balance:   {self.ending_balance:.2f}",
            f"Total P&L:        {self.total_pnl:+.2f}",
            f"Trades:           {len(self.trades)}",
            f"Win rate:         {self.win_rate:.1%}",
            f"Max drawdown:     {self.max_drawdown:.2f}",
        ]
        return "\n".join(lines)


# One pip = 0.0001 for most FX pairs, 0.01 for JPY pairs, etc. Adjust per
# symbol as needed - kept as a simple constant here since this is a skeleton.
PIP_VALUE = 0.0001


class BacktestEngine:
    def __init__(
        self,
        candles: list[Candle],
        strategy: Callable[[list[Candle]], OrderParams | None],
        starting_balance: float = 10_000.0,
        pip_value: float = PIP_VALUE,
        spread_pips: float = 1.5,
        slippage_pips: float = 0.5,
        commission_per_lot: float = 7.0,
    ):
        """
        spread_pips: cost paid on every entry, modeling bid/ask spread -
            applied against you at entry (buy fills slightly worse, sell
            fills slightly worse), never in your favor.
        slippage_pips: extra adverse movement applied at both entry and
            exit, modeling the fact that real fills rarely land exactly
            on the price you requested. Applied as a worst-case constant
            here for simplicity - a more advanced version could randomize
            this within a range.
        commission_per_lot: flat currency cost charged per lot traded,
            round-turn (charged once per closed trade, not per side).
        """
        self.candles = candles
        self.strategy = strategy
        self.starting_balance = starting_balance
        self.pip_value = pip_value
        self.spread_pips = spread_pips
        self.slippage_pips = slippage_pips
        self.commission_per_lot = commission_per_lot
        self.balance = starting_balance
        self.open_position: Position | None = None
        self.trades: list[ClosedTrade] = []

    def run(self) -> BacktestResult:
        for i in range(1, len(self.candles)):
            history = self.candles[: i + 1]
            current = self.candles[i]

            if self.open_position:
                self._check_exit(current)

            if not self.open_position:
                order = self.strategy(history)
                if order is not None:
                    self._open_from_order(order, current)

        # Force-close anything still open at the end of the data
        if self.open_position:
            self._close_position(
                self.candles[-1].close, self.candles[-1].timestamp, "end_of_data"
            )

        return BacktestResult(
            starting_balance=self.starting_balance,
            ending_balance=self.balance,
            trades=self.trades,
        )

    def _open_from_order(self, order: OrderParams, candle: Candle) -> None:
        if order.dry_run:
            # A dry_run order is explicitly a no-op by schema design -
            # the strategy is signaling "would trade" without committing.
            return
        if order.action == Action.CLOSE:
            return  # nothing to close, no position open

        entry_price = candle.close
        pip = self.pip_value
        entry_cost_pips = self.spread_pips + self.slippage_pips

        if order.action == Action.BUY:
            # Buying: spread + slippage push your fill price UP (worse for you)
            entry_price += entry_cost_pips * pip
            sl_price = entry_price - order.sl_pips * pip
            tp_price = entry_price + order.tp_pips * pip
        else:  # SELL
            # Selling: spread + slippage push your fill price DOWN (worse for you)
            entry_price -= entry_cost_pips * pip
            sl_price = entry_price + order.sl_pips * pip
            tp_price = entry_price - order.tp_pips * pip

        self.open_position = Position(
            symbol=order.symbol,
            action=order.action,
            entry_price=entry_price,
            vol_lots=order.vol_lots,
            sl_price=sl_price,
            tp_price=tp_price,
            opened_at=candle.timestamp,
            trace_id=order.trace_id,
        )

    def _check_exit(self, candle: Candle) -> None:
        pos = self.open_position
        if pos is None:
            return

        if pos.action == Action.BUY:
            if candle.low <= pos.sl_price:
                self._close_position(pos.sl_price, candle.timestamp, "sl")
            elif candle.high >= pos.tp_price:
                self._close_position(pos.tp_price, candle.timestamp, "tp")
        else:  # SELL
            if candle.high >= pos.sl_price:
                self._close_position(pos.sl_price, candle.timestamp, "sl")
            elif candle.low <= pos.tp_price:
                self._close_position(pos.tp_price, candle.timestamp, "tp")

    def _close_position(
        self, exit_price: float, closed_at: datetime, reason: str
    ) -> None:
        pos = self.open_position
        assert pos is not None

        pip = self.pip_value
        # Exit slippage always works against you too - closing a long fills
        # slightly lower than requested, closing a short fills slightly higher.
        if pos.action == Action.BUY:
            exit_price -= self.slippage_pips * pip
        else:  # SELL
            exit_price += self.slippage_pips * pip

        direction = 1 if pos.action == Action.BUY else -1
        # Simplified P&L: price difference * lots * a notional contract size.
        # Replace 100_000 with your actual instrument's contract size.
        gross_pnl = direction * (exit_price - pos.entry_price) * pos.vol_lots * 100_000
        commission = self.commission_per_lot * pos.vol_lots
        pnl = gross_pnl - commission

        self.balance += pnl
        self.trades.append(
            ClosedTrade(
                symbol=pos.symbol,
                action=pos.action,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                vol_lots=pos.vol_lots,
                opened_at=pos.opened_at,
                closed_at=closed_at,
                pnl=pnl,
                exit_reason=reason,
            )
        )
        self.open_position = None


# ---------------------------------------------------------------------------
# Self-test with synthetic data and a trivial strategy, so you can confirm
# the engine runs before plugging in real historical data or real logic.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    from datetime import timedelta

    random.seed(42)
    candles: list[Candle] = []
    price = 1.1000
    start = datetime(2026, 1, 1)
    for i in range(500):
        change = random.uniform(-0.0015, 0.0015)
        open_p = price
        close_p = price + change
        high_p = max(open_p, close_p) + random.uniform(0, 0.0005)
        low_p = min(open_p, close_p) - random.uniform(0, 0.0005)
        candles.append(
            Candle(start + timedelta(hours=i), "EURUSD", open_p, high_p, low_p, close_p)
        )
        price = close_p

    def toy_strategy(history: list[Candle]) -> OrderParams | None:
        """
        Placeholder strategy: buy after 3 consecutive up-candles.
        Replace this with real logic - the point here is showing how a
        strategy plugs into the engine via OrderParams, not that this
        strategy is good (it isn't, it's just for the self-test).
        """
        if len(history) < 4:
            return None
        last3 = history[-3:]
        if all(c.close > c.open for c in last3):
            return OrderParams(
                strategy_name="toy_3_up_candles",
                action="buy",
                symbol=history[-1].symbol,
                vol_lots=0.1,
                sl_pips=30,
                tp_pips=60,
                max_account_risk_pct=0.5,
                dry_run=False,  # must explicitly opt in to simulate a real fill
            )
        return None

    engine = BacktestEngine(candles, toy_strategy, starting_balance=10_000.0)
    print(
        f"Running with spread={engine.spread_pips}p slippage={engine.slippage_pips}p "
        f"commission=${engine.commission_per_lot}/lot (all costs on by default)\n"
    )
    result = engine.run()
    print(result.summary())
