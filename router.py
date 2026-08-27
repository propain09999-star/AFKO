"""
router.py — decides whether a classified file belongs to an existing
repo, or should be queued toward creating a new one (subject to the
new_repo_threshold and new_repo_requires_confirmation gates in config).
"""

import json
import os
from datetime import datetime, timezone


def list_existing_repos(repo_base_path: str) -> list:
    """Returns directory names under repo_base_path that look like git repos."""
    base = os.path.expanduser(repo_base_path)
    if not os.path.isdir(base):
        return []
    return [
        name for name in os.listdir(base)
        if os.path.isdir(os.path.join(base, name, ".git"))
    ]


def find_matching_repo(slug: str, existing_repos: list) -> str:
    """
    Exact match first, then a loose substring match (handles the model
    returning e.g. "radio-notes-2" when "radio-notes" already exists).
    Returns the matched repo name, or None if nothing matches.
    """
    if slug in existing_repos:
        return slug
    for repo in existing_repos:
        if slug in repo or repo in slug:
            return repo
    return None


def count_pending_for_slug(pending_log_path: str, slug: str) -> int:
    if not os.path.exists(pending_log_path):
        return 0
    count = 0
    with open(pending_log_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("slug") == slug and not entry.get("resolved"):
                count += 1
    return count


def append_pending(pending_log_path: str, file_path: str, classification: dict):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file_path": file_path,
        "slug": classification["slug"],
        "summary": classification.get("summary", ""),
        "tags": classification.get("tags", []),
        "resolved": False,
    }
    with open(pending_log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def route(file_path: str, classification: dict, cfg: dict) -> dict:
    """
    Returns one of:
      {"action": "existing_repo", "repo": <name>}
      {"action": "pending", "reason": <str>}                  — below threshold
      {"action": "needs_confirmation", "slug": <str>, "count": N}  — at threshold, awaiting human OK
      {"action": "create_repo", "slug": <str>}                — confirmation not required, threshold met
    """
    slug = classification["slug"]
    existing_repos = list_existing_repos(cfg["repo_base_path"])

    matched = find_matching_repo(slug, existing_repos)
    if matched:
        return {"action": "existing_repo", "repo": matched}

    pending_log_path = cfg["pending_log"]
    append_pending(pending_log_path, file_path, classification)
    pending_count = count_pending_for_slug(pending_log_path, slug)

    threshold = cfg.get("new_repo_threshold", 3)
    if pending_count < threshold:
        return {
            "action": "pending",
            "reason": f"{pending_count}/{threshold} files classified as '{slug}' so far — waiting for more before creating a repo",
        }

    if cfg.get("new_repo_requires_confirmation", True):
        return {"action": "needs_confirmation", "slug": slug, "count": pending_count}

    return {"action": "create_repo", "slug": slug}
  
