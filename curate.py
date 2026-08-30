#!/usr/bin/env python3
"""
curate.py -- move a file into its repo, update INDEX.md with a summary
entry, then commit (and push, if not requiring confirmation).
"""

import datetime
import os
import shutil
import subprocess
import urllib.request


def add_to_index(repo_path, filename, summary, tags):
    index_path = os.path.join(repo_path, "INDEX.md")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write("# Index\n\n")

    date = datetime.date.today().isoformat()
    tag_str = ", ".join(tags) if tags else ""
    line = f"- **{date}** — `{filename}` — {summary}"
    if tag_str:
        line += f" _(tags: {tag_str})_"
    line += "\n"

    with open(index_path, "a") as f:
        f.write(line)


def place_file(src_path, repo_path):
    filename = os.path.basename(src_path)
    dest_dir = os.path.join(repo_path, "files")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    shutil.move(src_path, dest_path)
    return dest_path


def notify(ntfy_topic, title, message):
    if not ntfy_topic or ntfy_topic == "your-ntfy-topic-here":
        return
    url = f"https://ntfy.sh/{ntfy_topic}"
    req = urllib.request.Request(
        url, data=message.encode("utf-8"),
        headers={"Title": title}, method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # notification failures shouldn't break the pipeline


def commit_and_push(repo_path, filename, summary, push=True):
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    msg = f"auto: ingest {filename} -- {summary[:60]}"
    subprocess.run(["git", "commit", "-m", msg], cwd=repo_path, check=False)
    if push:
        subprocess.run(["git", "push"], cwd=repo_path, check=False)


def curate(src_path, repo_path, classification, require_confirmation, ntfy_topic):
    filename = os.path.basename(src_path)
    summary = classification.get("summary", "")
    tags = classification.get("tags", [])

    dest_path = place_file(src_path, repo_path)
    add_to_index(repo_path, filename, summary, tags)

    if require_confirmation:
        notify(
            ntfy_topic,
            title=f"repo-curator: review {filename}",
            message=f"Staged in {os.path.basename(repo_path)} -> {summary}\n"
                    f"Run curate.py --push {repo_path} to commit+push.",
        )
        return dest_path  # commit happens manually / on confirmation

    commit_and_push(repo_path, filename, summary, push=True)
    return dest_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--push":
        commit_and_push(sys.argv[2], "manual confirm", "manually confirmed batch", push=True)
    else:
        print("usage: curate.py --push <repo_path>")
