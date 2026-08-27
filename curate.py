"""
curate.py — moves a classified file into its target repo, updates
INDEX.md with an entry, and commits/pushes. Everything here respects
cfg["dry_run"] — when true, this logs exactly what WOULD happen
without touching the filesystem or git at all.
"""

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone


def update_index(repo_dir: str, filename: str, summary: str, tags: list):
    """Appends a row to INDEX.md, creating it with a header if absent."""
    index_path = os.path.join(repo_dir, "INDEX.md")
    is_new = not os.path.exists(index_path)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tags_str = ", ".join(tags) if tags else ""
    row = f"| {date_str} | {filename} | {summary} | {tags_str} |\n"

    with open(index_path, "a") as f:
        if is_new:
            f.write("# Index\n\n")
            f.write("| Date | File | Summary | Tags |\n")
            f.write("|---|---|---|---|\n")
        f.write(row)


def git_commit_and_push(repo_dir: str, filename: str, cfg: dict) -> dict:
    git_cfg = cfg["git"]
    pat = os.environ.get(git_cfg["pat_env_var"], "")
    if not pat:
        return {"error": f"{git_cfg['pat_env_var']} not set in environment — cannot push"}

    commands = [
        ["git", "-C", repo_dir, "config", "user.name", git_cfg["commit_author_name"]],
        ["git", "-C", repo_dir, "config", "user.email", git_cfg["commit_author_email"]],
        ["git", "-C", repo_dir, "add", "-A"],
        ["git", "-C", repo_dir, "commit", "-m", f"auto: ingest {filename}"],
        ["git", "-C", repo_dir, "push"],
    ]

    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # "nothing to commit" isn't a real failure — file might've
            # already been committed by a previous run
            if "nothing to commit" in result.stdout:
                continue
            return {"error": f"'{' '.join(cmd)}' failed: {result.stderr.strip()}"}

    return {"success": True}


def curate(file_path: str, repo_dir: str, classification: dict, cfg: dict) -> dict:
    """
    Moves file_path into repo_dir, updates INDEX.md, commits, pushes.
    Returns a result dict describing what happened (or would happen,
    under dry_run) — always logged by the caller regardless of mode.
    """
    filename = os.path.basename(file_path)
    dest_path = os.path.join(repo_dir, filename)
    summary = classification.get("summary", "")
    tags = classification.get("tags", [])

    if cfg.get("dry_run", True):
        return {
            "dry_run": True,
            "would_move_to": dest_path,
            "would_update_index_with": summary,
            "would_commit_message": f"auto: ingest {filename}",
        }

    os.makedirs(repo_dir, exist_ok=True)
    shutil.move(file_path, dest_path)
    update_index(repo_dir, filename, summary, tags)

    push_result = git_commit_and_push(repo_dir, filename, cfg)
    return {"dry_run": False, "moved_to": dest_path, **push_result}


def create_new_repo(slug: str, cfg: dict) -> dict:
    """
    Creates a new local repo directory with git init — does NOT create
    the remote on GitHub, since that needs an API call this script
    doesn't make (avoids silently creating repos on your account with
    no visibility). You create the remote once, manually, then this
    can push to it going forward.
    """
    repo_dir = os.path.join(os.path.expanduser(cfg["repo_base_path"]), slug)

    if cfg.get("dry_run", True):
        return {"dry_run": True, "would_create": repo_dir}

    os.makedirs(repo_dir, exist_ok=True)
    result = subprocess.run(["git", "-C", repo_dir, "init"], capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": f"git init failed: {result.stderr.strip()}"}

    with open(os.path.join(repo_dir, "README.md"), "w") as f:
        f.write(f"# {slug}\n\nAuto-created by auto-ingest. Files here were classified as belonging to this topic.\n")

    return {
        "dry_run": False,
        "created": repo_dir,
        "note": "local repo only — create the remote on GitHub and run "
                "`git remote add origin <url>` manually before the next push",
          }
  
