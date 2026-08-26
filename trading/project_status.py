"""
project_status.py

A checklist, not an agent. This script makes no decisions and takes no
actions - it inspects what actually exists and passes in the repo, and
reports which stage of the pipeline you're really at versus which stage
it might feel like you're at.

The sequence it checks against (same one we've been following):
  1. Schema exists and is syntactically valid
  2. Backtest engine exists and runs without crashing
  3. A real strategy (not just the toy placeholder) exists
  4. Realistic costs (spread/slippage/commission) are modeled
  5. Real historical data has been loaded at least once (not just synthetic)
  6. CI backtest regression check is wired up
  7. Paper trading adapter exists (NOT checked yet - none built)
  8. Live execution gate exists (NOT checked yet - none built, and
     shouldn't be until 1-7 are solid and you've watched paper trading
     run for a real stretch of time)

Run it any time you want an honest read on where things stand:
    python project_status.py
"""

from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent


def _file_exists(name: str) -> bool:
    return (REPO_ROOT / name).exists()


def _module_importable(name: str) -> bool:
    try:
        spec = importlib.util.spec_from_file_location(name, REPO_ROOT / f"{name}.py")
        if spec is None or spec.loader is None:
            return False
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True
    except Exception:
        return False


def check_schema() -> tuple[bool, str]:
    if not _file_exists("orchestration_schema.py"):
        return False, "orchestration_schema.py not found"
    if not _module_importable("orchestration_schema"):
        return False, "orchestration_schema.py exists but fails to import (check for syntax/dependency errors)"
    return True, "Schema exists and imports cleanly"


def check_backtest_engine() -> tuple[bool, str]:
    if not _file_exists("backtest_engine.py"):
        return False, "backtest_engine.py not found"
    try:
        spec = importlib.util.spec_from_file_location("backtest_engine", REPO_ROOT / "backtest_engine.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Actually try running the engine's own self-test data through it
        import random
        from datetime import datetime, timedelta

        random.seed(1)
        candles = []
        price = 1.10
        start = datetime(2026, 1, 1)
        for i in range(100):
            close_p = price + random.uniform(-0.001, 0.001)
            candles.append(module.Candle(start + timedelta(hours=i), "EURUSD", price, max(price, close_p), min(price, close_p), close_p))
            price = close_p

        def noop_strategy(history):
            return None

        engine = module.BacktestEngine(candles, noop_strategy)
        engine.run()
        return True, "Backtest engine runs without crashing"
    except Exception as e:
        return False, f"Backtest engine exists but crashed when run: {e}"


def check_real_strategy() -> tuple[bool, str]:
    strategy_files = list(REPO_ROOT.glob("strategy_*.py"))
    if not strategy_files:
        return False, "No strategy_*.py files found"
    names = [f.name for f in strategy_files]
    return True, f"Found strategy file(s): {', '.join(names)}"


def check_realistic_costs() -> tuple[bool, str]:
    if not _file_exists("backtest_engine.py"):
        return False, "backtest_engine.py not found"
    content = (REPO_ROOT / "backtest_engine.py").read_text()
    has_spread = "spread_pips" in content
    has_slippage = "slippage_pips" in content
    has_commission = "commission_per_lot" in content
    if has_spread and has_slippage and has_commission:
        return True, "Spread, slippage, and commission are all modeled"
    missing = [n for n, present in [("spread", has_spread), ("slippage", has_slippage), ("commission", has_commission)] if not present]
    return False, f"Missing cost modeling: {', '.join(missing)}"


def check_real_data_loaded() -> tuple[bool, str]:
    if not _file_exists("data_loader.py"):
        return False, "data_loader.py not found"
    csv_files = [f for f in REPO_ROOT.glob("*.csv") if "sample" not in f.name.lower()]
    if not csv_files:
        return False, "data_loader.py exists but no non-sample CSV data found in repo (this check can't see data you've loaded but not committed - that's fine, just confirm manually)"
    return True, f"Found data file(s) beyond the sample: {', '.join(f.name for f in csv_files)}"


def check_ci_backtest() -> tuple[bool, str]:
    ci_paths = [
        REPO_ROOT / ".github" / "workflows" / "backtest-check.yml",
        REPO_ROOT / "workflows" / "backtest-check.yml",
    ]
    if any(p.exists() for p in ci_paths):
        return True, "Backtest CI workflow found"
    return False, "backtest-check.yml not found in .github/workflows/"


def check_paper_trading() -> tuple[bool, str]:
    # Deliberately not auto-detecting broker SDK imports here - this stage
    # should be a deliberate decision you make, not something that flips
    # to "done" because a library got installed for some other reason.
    return False, "Not built yet (expected at this stage - don't build this until stages 1-6 are solid)"


def check_live_gate() -> tuple[bool, str]:
    return False, "Not built yet (should not exist until paper trading has run for a real stretch of time)"


def main() -> None:
    checks = [
        ("1. Schema", check_schema),
        ("2. Backtest engine", check_backtest_engine),
        ("3. Real strategy", check_real_strategy),
        ("4. Realistic costs modeled", check_realistic_costs),
        ("5. Real historical data loaded", check_real_data_loaded),
        ("6. CI backtest regression check", check_ci_backtest),
        ("7. Paper trading adapter", check_paper_trading),
        ("8. Live execution gate", check_live_gate),
    ]

    print("=" * 60)
    print("PROJECT STATUS - trading pipeline")
    print("=" * 60)

    first_incomplete = None
    for label, check_fn in checks:
        passed, detail = check_fn()
        mark = "[x]" if passed else "[ ]"
        print(f"{mark} {label}")
        print(f"      {detail}")
        if not passed and first_incomplete is None:
            first_incomplete = label

    print("=" * 60)
    if first_incomplete:
        print(f"NEXT STEP: {first_incomplete}")
        print("(Stages are meant to be completed in order - later stages")
        print(" that show as failing don't matter yet if an earlier one isn't done.)")
    else:
        print("All checked stages complete. Paper trading and live gate are")
        print("deliberately not auto-detected - decide those steps yourself,")
        print("don't let a script wave them through.")
    print("=" * 60)


if __name__ == "__main__":
    main()
