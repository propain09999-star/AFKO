#!/usr/bin/env python3
"""
watch_ingest.py -- polls a downloads folder for new files and runs them
through classify -> route -> curate.

Simple polling loop (no watchdog dependency needed -- works fine over
Termux storage). Keeps a seen-files set on disk so restarts don't
reprocess everything.
"""

import json
import os
import time

import yaml

from classify import classify_text
from router import list_existing_repos, route, create_repo
from curate import curate

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
SEEN_FILE = os.path.expanduser("~/repo-curator-staging/seen.json")

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".log"}


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE) as f:
        return set(json.load(f))


def save_seen(seen):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def read_text_safely(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in TEXT_EXTENSIONS:
        return f"[binary or unsupported file: {os.path.basename(path)}]"
    try:
        with open(path, "r", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"[could not read file: {e}]"


def process_file(path, cfg):
    filename = os.path.basename(path)
    content = read_text_safely(path)
    existing_repos = list_existing_repos(cfg["repos_base"])

    result = classify_text(
        filename, content, existing_repos,
        model=cfg["model"], url=cfg["ollama_url"],
    )
    if result is None:
        print(f"[skip] could not classify {filename}")
        return

    decision = route(result, cfg["repos_base"], cfg["new_repo_threshold"])

    if decision[0] == "existing":
        repo_path = os.path.join(os.path.expanduser(cfg["repos_base"]), decision[1])
        curate(path, repo_path, result, cfg["require_confirmation"], cfg["ntfy_topic"])
        print(f"[curated] {filename} -> {decision[1]}")

    elif decision[0] == "new_repo":
        repo_path = create_repo(decision[1], cfg["repos_base"], cfg.get("git_remote_prefix"))
        curate(path, repo_path, result, cfg["require_confirmation"], cfg["ntfy_topic"])
        print(f"[new repo] {filename} -> {decision[1]}")

    else:  # staged
        staging = os.path.expanduser(cfg["staging_dir"])
        os.makedirs(staging, exist_ok=True)
        os.rename(path, os.path.join(staging, filename))
        print(f"[staged {decision[2]}/{cfg['new_repo_threshold']}] {filename} -> {decision[1]}")


def main():
    cfg = load_config()
    watch_dir = os.path.expanduser(cfg["watch_dir"])
    seen = load_seen()

    print(f"watching {watch_dir} every {cfg['poll_seconds']}s...")
    while True:
        try:
            for filename in os.listdir(watch_dir):
                full_path = os.path.join(watch_dir, filename)
                if full_path in seen or not os.path.isfile(full_path):
                    continue
                # skip files still being written (size check)
                size1 = os.path.getsize(full_path)
                time.sleep(1)
                size2 = os.path.getsize(full_path)
                if size1 != size2:
                    continue

                process_file(full_path, cfg)
                seen.add(full_path)
                save_seen(seen)

        except Exception as e:
            print(f"[error] {e}")

        time.sleep(cfg["poll_seconds"])


if __name__ == "__main__":
    main()
