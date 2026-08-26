"""
mt5_paper_adapter.py

Executes OrderParams (from orchestration_schema.py) against a MetaTrader 5
account via its Python API. This is the "stage 7: paper trading adapter"
piece from project_status.py.

SAFETY DESIGN - read before using:

1. HARD DEMO GATE: connect() checks the account's trade_mode via MT5's own
   API and refuses to proceed if it's anything other than ACCOUNT_TRADE_MODE_DEMO.
   This check happens on every connection, not just once - there's no way
   to accidentally point this at a real account and have it work. If you
   genuinely want live trading later, that needs a separate, deliberately
   built adapter with its own explicit gate - not a flag flipped on this one.

2. dry_run IS STILL RESPECTED even though this only ever touches a demo
   account. An OrderParams with dry_run=True logs what it would have done
   and returns without calling MT5 at all. This keeps the discipline
   consistent across backtest, paper, and (eventually, separately) live -
   the schema's safety behavior doesn't change based on which adapter is
   using it.

3. Every order and every rejection is logged with the trace_id, so you
   have a full audit trail of what was sent, what was rejected, and why.

REQUIREMENTS:
- Windows (or Linux/Mac via Wine) with MT5 terminal installed and logged
  into a DEMO account.
- pip install MetaTrader5
- This does NOT run on Android/Termux.
"""

from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import Optional

from orchestration_schema import OrderParams, Action

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package not installed, or not on a supported platform.")
    print("Install with: pip install MetaTrader5 (Windows only, or Linux/Mac via Wine)")
    sys.exit(1)


class NotADemoAccountError(Exception):
    """Raised when connect() detects the MT5 terminal is logged into
    anything other than a demo account. This is not catchable-and-ignorable
    by design in how this module is meant to be used - see the module
    docstring."""


@dataclass
class ExecutionResult:
    trace_id: str
    accepted: bool
    reason: str
    mt5_order_id: Optional[int] = None


def connect() -> None:
    """
    Initializes the MT5 connection and verifies the account is a demo
    account. Raises NotADemoAccountError if it isn't - this function will
    not return successfully on a real account under any circumstance.
    """
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        raise RuntimeError("Could not read account info from MT5 terminal.")

    if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        mt5.shutdown()
        raise NotADemoAccountError(
            f"Account {account.login} on server {account.server} is NOT a "
            f"demo account (trade_mode={account.trade_mode}). This adapter "
            f"refuses to run against anything but a demo account. Aborting "
            f"before any order logic runs."
        )

    print(f"Connected to DEMO account {account.login} on {account.server} "
          f"(balance: {account.balance} {account.currency})")


def disconnect() -> None:
    mt5.shutdown()


def execute_order(order: OrderParams) -> ExecutionResult:
    """
    Sends one validated order to the (already-confirmed-demo) MT5 account.
    Returns an ExecutionResult - never raises for a rejected/invalid order,
    only for connection-level failures, so callers can log rejections
    without crashing a run.
    """
    if order.dry_run:
        print(f"[DRY RUN] {order.trace_id}: would send {order.action.value} "
              f"{order.vol_lots} lots {order.symbol} - not sent to MT5.")
        return ExecutionResult(order.trace_id, accepted=False, reason="dry_run")

    if order.action == Action.CLOSE:
        return _close_position(order)

    tick = mt5.symbol_info_tick(order.symbol)
    if tick is None:
        return ExecutionResult(order.trace_id, accepted=False, reason=f"no tick data for {order.symbol}")

    symbol_info = mt5.symbol_info(order.symbol)
    if symbol_info is None:
        return ExecutionResult(order.trace_id, accepted=False, reason=f"unknown symbol {order.symbol}")
    point = symbol_info.point

    if order.action == Action.BUY:
        price = tick.ask
        order_type = mt5.ORDER_TYPE_BUY
        sl = price - order.sl_pips * point * 10  # *10 accounts for 5-digit brokers; verify for your broker
        tp = price + order.tp_pips * point * 10
    else:  # SELL
        price = tick.bid
        order_type = mt5.ORDER_TYPE_SELL
        sl = price + order.sl_pips * point * 10
        tp = price - order.tp_pips * point * 10

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": order.symbol,
        "volume": order.vol_lots,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 20260826,  # arbitrary identifier for orders from this bot
        "comment": f"{order.strategy_name[:20]}|{order.trace_id[:16]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None:
        return ExecutionResult(order.trace_id, accepted=False, reason=f"order_send returned None: {mt5.last_error()}")

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return ExecutionResult(
            order.trace_id, accepted=False,
            reason=f"MT5 rejected order, retcode={result.retcode}: {result.comment}"
        )

    print(f"[PAPER FILL] {order.trace_id}: {order.action.value} {order.vol_lots} "
          f"{order.symbol} @ {price} (MT5 order #{result.order})")
    return ExecutionResult(order.trace_id, accepted=True, reason="filled", mt5_order_id=result.order)


def _close_position(order: OrderParams) -> ExecutionResult:
    positions = mt5.positions_get(symbol=order.symbol)
    if not positions:
        return ExecutionResult(order.trace_id, accepted=False, reason=f"no open position on {order.symbol} to close")

    pos = positions[0]
    tick = mt5.symbol_info_tick(order.symbol)
    close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": order.symbol,
        "volume": pos.volume,
        "type": close_type,
        "position": pos.ticket,
        "price": price,
        "deviation": 10,
        "magic": 20260826,
        "comment": f"close|{order.trace_id[:16]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        reason = f"close failed: {mt5.last_error() if result is None else result.comment}"
        return ExecutionResult(order.trace_id, accepted=False, reason=reason)

    return ExecutionResult(order.trace_id, accepted=True, reason="closed", mt5_order_id=result.order)


if __name__ == "__main__":
    # Self-check only - connects, verifies demo status, prints account info,
    # disconnects. Does NOT place any order. Run this first to confirm the
    # demo gate works before wiring up any real strategy loop.
    try:
        connect()
        print("Demo gate check passed. No orders were placed by this self-check.")
    except NotADemoAccountError as e:
        print(f"BLOCKED: {e}")
        sys.exit(1)
    finally:
        disconnect()
  
