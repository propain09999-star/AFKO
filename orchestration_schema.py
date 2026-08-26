"""
orchestration_schema.py

Strict, explicitly-typed schema for every order your trading logic produces.
Goal: kill "vague system interpretation" bugs by making every strategy function
read/write exactly this shape - nothing looser, nothing implicit.

Every strategy function should return an OrderParams instance, not a dict,
not a tuple, not a bare string. If a strategy can't populate every required
field with a real, validated value, it shouldn't produce an order.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"


class OrderParams(BaseModel):
    """
    The one and only shape an order can take. No strategy function should
    build orders any other way - this replaces ad-hoc dicts / loose strings.
    """

    # --- Identity & audit trail ---
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    strategy_name: str = Field(..., min_length=1, max_length=64)

    # --- Core order fields ---
    action: Action
    symbol: str = Field(..., min_length=1, max_length=20)
    vol_lots: float = Field(..., gt=0, le=100)  # hard ceiling - see MAX_LOTS below
    sl_pips: float = Field(..., gt=0, le=1000)
    tp_pips: float = Field(..., gt=0, le=5000)

    # --- Risk / safety metadata (required, not optional - forces the caller
    #     to actually think about these instead of leaving them unset) ---
    max_account_risk_pct: float = Field(..., gt=0, le=2.0)
    dry_run: bool = True  # must be explicitly flipped to False to go live

    # --- Optional context, purely informational, never used for logic ---
    notes: Optional[str] = Field(default=None, max_length=280)

    # Hard system-wide ceiling. A strategy can request less; it can never
    # request more than this no matter what the field-level validator allows.
    MAX_LOTS_PER_ORDER: float = 5.0

    @field_validator("symbol")
    @classmethod
    def symbol_upper(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalnum():
            raise ValueError(f"symbol must be alphanumeric, got: {v!r}")
        return v

    @field_validator("action", mode="before")
    @classmethod
    def action_lower(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="after")
    def enforce_hard_caps(self) -> "OrderParams":
        if self.vol_lots > self.MAX_LOTS_PER_ORDER:
            raise ValueError(
                f"vol_lots {self.vol_lots} exceeds hard system cap "
                f"{self.MAX_LOTS_PER_ORDER} - reduce position size, "
                f"do not raise the cap to fit the trade."
            )
        if self.action == Action.CLOSE and (self.sl_pips or self.tp_pips):
            # closing an existing position doesn't need new SL/TP targets
            raise ValueError("CLOSE orders should not carry sl_pips/tp_pips")
        return self

    class Config:
        use_enum_values = False
        frozen = True  # once built, an order can't be silently mutated


# ---------------------------------------------------------------------------
# Example usage / self-test. Run this file directly to see validation in
# action - both the happy path and a rejected order.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    good = OrderParams(
        strategy_name="mean_reversion_v1",
        action="buy",
        symbol="btcusd",
        vol_lots=0.5,
        sl_pips=50,
        tp_pips=100,
        max_account_risk_pct=0.5,
        dry_run=True,
    )
    print("Valid order built:")
    print(good.model_dump_json(indent=2))

    print("\nAttempting an order that exceeds the hard lot cap...")
    try:
        OrderParams(
            strategy_name="overconfident_v2",
            action="buy",
            symbol="ETHUSD",
            vol_lots=50,  # way over MAX_LOTS_PER_ORDER
            sl_pips=50,
            tp_pips=100,
            max_account_risk_pct=1.0,
        )
    except Exception as e:
        print(f"Rejected as expected: {e}")
