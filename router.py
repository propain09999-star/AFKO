#!/usr/bin/env python3
"""
router.py -- decide where a classified file should go:
  - an existing repo
  - the staging area (not enough files yet to justify a new repo)
  - a brand new repo (staging threshold hit)

No classes. State is just a small JSON file tracking staging counts.
"""

import json
import os
import subprocess

STATE_FILE = os.path.expanduser("~/repo-curator-staging/state.json")


def list_existing_repos(repos_base):
    repos_base = os.path.expanduser(repos_base)
    if not os.path.isdir(repos_base):
        return []
    return [
        d for d in os.listdir(repos_base)
        if os.path.isdir(os.path.join(repos_base, d, ".git"))
    ]


def _load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def route(classification, repos_base, threshold):
    """
    Returns one of:
      ("existing", repo_slug)
      ("staged", repo_slug, count_so_far)
      ("new_repo", repo_slug)
    """
    slug = classification["repo_slug"]
    existing = list_existing_repos(repos_base)

    if classification.get("is_existing") and slug in existing:
        return ("existing", slug)

    if slug in existing:
        return ("existing", slug)

    # not an existing repo -- check staging count
    state = _load_state()
    count = state.get(slug, 0) + 1
    state[slug] = count
    _save_state(state)

    if count >= threshold:
        return ("new_repo", slug)
    return ("staged", slug, count)


def create_repo(slug, repos_base, git_remote_prefix=None):
    """git init a new local repo for this slug. Push happens later in curate.py."""
    repos_base = os.path.expanduser(repos_base)
    path = os.path.join(repos_base, slug)
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)
    with open(os.path.join(path, "README.md"), "w") as f:
        f.write(f"# {slug}\n\nAuto-created by repo-curator.\n")
    with open(os.path.join(path, "INDEX.md"), "w") as f:
        f.write(f"# Index\n\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init: auto-created repo"], cwd=path, check=True)

    if git_remote_prefix:
        remote_url = f"{git_remote_prefix}{slug}.git"
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=path, check=False)

    # clear staging count now that it's graduated
    state = _load_state()
    state.pop(slug, None)
    _save_state(state)

    return path
