#!/usr/bin/env python3
"""
Compares pipeline output (before vs after a fix/dependency bump) and
reports any behavioral difference. Used by canary-automerge.yml and
auto-fix-isolated.yml to catch fixes that silently change what the
pipeline actually does, not just whether it crashes.

Usage:
    python diff_pipeline_output.py --baseline before.json --current after.json
Exit code 0 always (this is a reporting tool, not a hard gate) — prints
to stdout, and the calling workflow decides what to do with the result.
"""
import argparse
import json
import sys

# Fields that are EXPECTED to differ between runs and should be ignored
# (timestamps, run IDs, etc.) — add to this list as you find more.
IGNORE_KEYS = {"timestamp", "run_id", "processing_time_ms", "generated_at"}


def strip_ignored(obj):
    if isinstance(obj, dict):
        return {k: strip_ignored(v) for k, v in obj.items() if k not in IGNORE_KEYS}
    if isinstance(obj, list):
        return [strip_ignored(v) for v in obj]
    return obj


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"WARNING: could not load {path}: {e}", file=sys.stderr)
        return {}


def diff_dicts(baseline, current, path=""):
    """Yield human-readable lines describing every difference."""
    diffs = []
    all_keys = set(baseline.keys()) | set(current.keys())
    for key in sorted(all_keys):
        full_path = f"{path}.{key}" if path else key
        b_val = baseline.get(key, "<missing>")
        c_val = current.get(key, "<missing>")

        if key not in baseline:
            diffs.append(f"+ NEW FIELD  {full_path}: {c_val!r}")
        elif key not in current:
            diffs.append(f"- REMOVED    {full_path}: {b_val!r}")
        elif isinstance(b_val, dict) and isinstance(c_val, dict):
            diffs.extend(diff_dicts(b_val, c_val, full_path))
        elif isinstance(b_val, list) and isinstance(c_val, list):
            if b_val != c_val:
                diffs.append(f"~ CHANGED    {full_path}:")
                diffs.append(f"    before: {b_val!r}")
                diffs.append(f"    after:  {c_val!r}")
        elif b_val != c_val:
            diffs.append(f"~ CHANGED    {full_path}: {b_val!r} -> {c_val!r}")
    return diffs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--current", required=True)
    args = parser.parse_args()

    baseline = strip_ignored(load_json(args.baseline))
    current = strip_ignored(load_json(args.current))

    diffs = diff_dicts(baseline, current)

    if not diffs:
        # Empty stdout is treated by the calling workflow as "no diff"
        return

    print(f"Behavior diff: {len(diffs)} field(s) changed between baseline and current run\n")
    for line in diffs:
        print(line)


if __name__ == "__main__":
    main()
    
