"""
watch_ingest.py — polls a folder for new files and runs each one
through classify -> route -> curate. No watchdog dependency: a simple
poll loop is enough for a downloads folder and keeps deps minimal.

Usage:
    python watch_ingest.py [--config config.yaml] [--once]

--once processes whatever's currently in the folder and exits,
instead of looping forever — useful for testing and for running via
cron/Termux:Boot instead of a long-lived process.
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone

import yaml

from classify import classify_file
from router import route
from curate import curate, create_new_repo


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def log_decision(decision_log_path: str, entry: dict):
    with open(decision_log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def process_file(file_path: str, cfg: dict) -> dict:
    """
    Runs one file through the full pipeline. Returns the full decision
    record (what was classified, routed, and curated as) — this is
    what gets written to decision_log regardless of outcome, so a
    misclassification is debuggable after the fact.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": file_path,
    }

    classification = classify_file(file_path, cfg)
    record["classification"] = classification

    if "error" in classification:
        record["outcome"] = "classification_failed"
        return record

    routing = route(file_path, classification, cfg)
    record["routing"] = routing

    if routing["action"] == "existing_repo":
        repo_dir = os.path.join(os.path.expanduser(cfg["repo_base_path"]), routing["repo"])
        record["curation"] = curate(file_path, repo_dir, classification, cfg)
        record["outcome"] = "curated"

    elif routing["action"] == "pending":
        record["outcome"] = "pending_more_files_needed"

    elif routing["action"] == "needs_confirmation":
        record["outcome"] = "awaiting_human_confirmation"
        record["confirmation_needed_for_slug"] = routing["slug"]
        # NOTE: this is where a real confirmation channel (ntfy.sh
        # push, a Termux notification, a Slack message — pick one)
        # should ask "create repo '<slug>'? y/n" and only proceed on
        # yes. Not wired up here — see NEXT STEPS.

    elif routing["action"] == "create_repo":
        creation = create_new_repo(routing["slug"], cfg)
        record["repo_creation"] = creation
        if not creation.get("dry_run") and "error" not in creation:
            repo_dir = creation["created"]
            record["curation"] = curate(file_path, repo_dir, classification, cfg)
        record["outcome"] = "repo_created_and_curated" if "error" not in creation else "repo_creation_failed"

    return record


def scan_once(cfg: dict, seen: set) -> set:
    """Processes any new files in watch_dir not already in `seen`. Returns updated seen set."""
    watch_dir = os.path.expanduser(cfg["watch_dir"])
    if not os.path.isdir(watch_dir):
        print(f"[watch_ingest] watch_dir does not exist: {watch_dir}")
        return seen

    for filename in os.listdir(watch_dir):
        file_path = os.path.join(watch_dir, filename)
        if file_path in seen or not os.path.isfile(file_path):
            continue
        if os.path.getsize(file_path) < cfg.get("min_file_size_bytes", 16):
            continue  # likely still being written

        print(f"[watch_ingest] processing {filename}")
        record = process_file(file_path, cfg)
        log_decision(cfg["decision_log"], record)
        print(f"[watch_ingest]   -> {record['outcome']}")

        seen.add(file_path)

    return seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--once", action="store_true", help="Process current files and exit, don't loop")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if cfg.get("dry_run", True):
        print("[watch_ingest] DRY RUN — no files will be moved, no commits/pushes will happen")

    seen = set()

    if args.once:
        scan_once(cfg, seen)
        return

    print(f"[watch_ingest] watching {cfg['watch_dir']} every {cfg['poll_interval_seconds']}s (Ctrl+C to stop)")
    try:
        while True:
            seen = scan_once(cfg, seen)
            time.sleep(cfg.get("poll_interval_seconds", 30))
    except KeyboardInterrupt:
        print("\n[watch_ingest] stopped.")


if __name__ == "__main__":
    main()
