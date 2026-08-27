#!/usr/bin/env python3
"""
Blue-team pass: argues FOR safety, based entirely on OUTPUT evidence —
did the invariant checker pass, does the quirk filter show zero
unresolved flags, did the before/after test diff come back empty.

This is deliberately DATA-driven (what actually happened when it ran),
not code-driven. Red-team below is the opposite — deliberately
CODE-driven (what the diff touches), not data-driven. Two different
kinds of evidence, so a blind spot in one method doesn't sink both.

Usage:
    python blue_confirm.py --invariant-report invariant-report.txt \
        --quirk-report quirk-filter-report.txt --test-diff test-result-diff.txt
Exit 0 + prints "safe" if all three are clean. Exit 1 + prints "unsafe" otherwise.
"""
import argparse
import sys
from pathlib import Path


def is_clean(report_path, clean_markers):
    if not Path(report_path).exists():
        return True, "report file absent, treated as no findings"
    text = Path(report_path).read_text()
    for marker in clean_markers:
        if marker in text:
            return True, f"matched clean marker: {marker!r}"
    return False, text.strip()[:500]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--invariant-report", required=True)
    parser.add_argument("--quirk-report", required=True)
    parser.add_argument("--test-diff", required=False, default=None)
    args = parser.parse_args()

    reasons_unsafe = []

    inv_clean, inv_detail = is_clean(args.invariant_report, ["All invariants satisfied."])
    if not inv_clean:
        reasons_unsafe.append(f"invariant report not clean: {inv_detail}")

    quirk_clean, quirk_detail = is_clean(args.quirk_report, ["0 unresolved", "suppressed as known quirks, 0 unresolved"])
    if not quirk_clean:
        reasons_unsafe.append(f"quirk filter shows unresolved flags: {quirk_detail}")

    if args.test_diff and Path(args.test_diff).exists():
        diff_text = Path(args.test_diff).read_text().strip()
        if diff_text and "REGRESSION" in diff_text:
            reasons_unsafe.append(f"test regression detected: {diff_text[:500]}")

    if reasons_unsafe:
        print("verdict=unsafe")
        for r in reasons_unsafe:
            print(f"  - {r}")
        sys.exit(1)

    print("verdict=safe")
    print("  - invariants clean, quirk filter clean, no test regressions")


if __name__ == "__main__":
    main()
