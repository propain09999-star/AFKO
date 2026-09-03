#!/usr/bin/env python3
"""
Red-team pass: independently tries to find why a change is NOT safe,
using CODE-structure evidence — what the diff actually touches — not
runtime output. This deliberately can't share blue_confirm.py's blind
spot: blue only sees what the code DID when it ran once against one
fixture; red looks at what the code COULD do based on what changed,
regardless of whether the one test run happened to exercise it.

Checks (each is a real, independent heuristic — not a rephrasing of
the same signal):
  1. Diff touches a file/path listed as high-risk (contracts/high-risk-paths.yml)
  2. Diff changes code but touches zero test files (untested change)
  3. Diff REMOVES an assertion, invariant entry, or test rather than adding one
  4. Diff touches a security-sensitive pattern (subprocess, eval, raw SQL, network calls)
  5. Diff size exceeds a threshold (large diffs get flagged for review regardless)

Usage:
    python red_falsify.py --diff pr.diff --high-risk-paths contracts/high-risk-paths.yml
Exit 0 + "safe" if none trigger. Exit 1 + "unsafe" with reasons otherwise.
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

SENSITIVE_PATTERNS = [
    r"\bsubprocess\.",
    r"\beval\(",
    r"\bexec\(",
    r"\bos\.system\(",
    r"requests\.(get|post)\(",
    r"\bpickle\.loads\(",
]

MAX_DIFF_LINES = 300


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", required=True, help="unified diff, e.g. from `git diff main...HEAD`")
    parser.add_argument("--high-risk-paths", default="contracts/high-risk-paths.yml")
    args = parser.parse_args()

    diff_text = Path(args.diff).read_text()
    lines = diff_text.splitlines()

    reasons = []

    # 1. high-risk paths
    try:
        with open(args.high_risk_paths) as f:
            risk_config = yaml.safe_load(f) or {}
        high_risk = risk_config.get("high_risk_paths", [])
    except FileNotFoundError:
        high_risk = []

    touched_files = [l[6:] for l in lines if l.startswith("+++ b/")]
    for f in touched_files:
        for risk_path in high_risk:
            if risk_path in f:
                reasons.append(f"touches high-risk path: {f} (matches policy entry {risk_path!r})")

    # 2. code changed, no test files touched
    code_touched = any(f.endswith(".py") and "test" not in f for f in touched_files)
    test_touched = any("test" in f for f in touched_files)
    if code_touched and not test_touched:
        reasons.append("modifies code but touches zero test files")

    # 3. removed assertions/invariants/tests (lines starting with '-' containing assert/invariant)
    removed_checks = [l for l in lines if l.startswith("-") and not l.startswith("---")
                       and re.search(r"\b(assert|invariant|def test_)\b", l)]
    if removed_checks:
        reasons.append(f"removes {len(removed_checks)} assertion/invariant/test line(s) rather than adding")

    # 4. security-sensitive patterns introduced
    added_lines = [l for l in lines if l.startswith("+") and not l.startswith("+++")]
    for pattern in SENSITIVE_PATTERNS:
        hits = [l for l in added_lines if re.search(pattern, l)]
        if hits:
            reasons.append(f"introduces sensitive pattern {pattern!r}: {hits[0].strip()}")

    # 5. diff size
    changed_line_count = len(added_lines) + len([l for l in lines if l.startswith("-") and not l.startswith("---")])
    if changed_line_count > MAX_DIFF_LINES:
        reasons.append(f"large diff ({changed_line_count} lines changed) — flagged for review regardless of content")

    if reasons:
        print("verdict=unsafe")
        for r in reasons:
            print(f"  - {r}")
        sys.exit(1)

    print("verdict=safe")
    print("  - no high-risk paths touched, tests accompany code changes, no assertions removed, no sensitive patterns introduced, diff size acceptable")


if __name__ == "__main__":
    main()
    
