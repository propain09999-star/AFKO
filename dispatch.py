#!/usr/bin/env python3
"""
Termux-side dispatcher: sends a heavy task to GitHub Actions,
waits for it to finish, pulls the result back, and pushes an
ntfy.sh notification (same pattern as repo-curator).

Usage:
    python3 dispatch.py "extract the sweepstakes details as JSON" json_extract

Env vars required:
    GH_PAT       - GitHub personal access token (repo scope)
    GH_REPO      - "you/repo"
    NTFY_TOPIC   - your ntfy.sh topic (optional, defaults to "your-topic")
"""
import base64
import json
import os
import sys
import time

import requests

GH_PAT = os.environ.get("GH_PAT")
REPO = os.environ.get("GH_REPO", "you/repo")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "your-topic")
WORKFLOW_FILE = "heavy-task-dispatch.yml"
API_BASE = f"https://api.github.com/repos/{REPO}"
POLL_INTERVAL = 10
POLL_TIMEOUT = 600


def dispatch(headers, prompt: str, task_type: str):
    body = {
        "event_type": "heavy_task",
        "client_payload": {"prompt": prompt, "task_type": task_type},
    }
    resp = requests.post(f"{API_BASE}/dispatches", headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    print("Dispatched. Waiting for the workflow to pick it up...")


def get_latest_run(headers):
    resp = requests.get(
        f"{API_BASE}/actions/workflows/{WORKFLOW_FILE}/runs",
        headers=headers,
        params={"per_page": 1},
        timeout=30,
    )
    resp.raise_for_status()
    runs = resp.json().get("workflow_runs", [])
    return runs[0] if runs else None


def wait_for_completion(headers):
    start = time.time()
    run_id = None

    # wait for a fresh run to show up
    while time.time() - start < POLL_TIMEOUT and run_id is None:
        run = get_latest_run(headers)
        if run and run["status"] != "completed":
            run_id = run["id"]
        else:
            time.sleep(POLL_INTERVAL)

    if run_id is None:
        run = get_latest_run(headers)
        run_id = run["id"] if run else None
    if run_id is None:
        raise RuntimeError("No workflow run found")

    while time.time() - start < POLL_TIMEOUT:
        resp = requests.get(f"{API_BASE}/actions/runs/{run_id}", headers=headers, timeout=30)
        resp.raise_for_status()
        run = resp.json()
        if run["status"] == "completed":
            return run
        time.sleep(POLL_INTERVAL)

    raise TimeoutError("Timed out waiting for the workflow run to complete")


def fetch_result(headers):
    # Assumes the workflow commits result.json back to the default branch
    resp = requests.get(f"{API_BASE}/contents/result.json", headers=headers, timeout=30)
    resp.raise_for_status()
    content = base64.b64decode(resp.json()["content"]).decode()
    return json.loads(content)


def notify(message: str):
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode(), timeout=10)
    except Exception:
        pass


def main():
    if len(sys.argv) < 2:
        print("Usage: dispatch.py <prompt> [task_type]", file=sys.stderr)
        sys.exit(1)
    if not GH_PAT:
        print("Set GH_PAT env var", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    task_type = sys.argv[2] if len(sys.argv) > 2 else "reasoning"
    headers = {"Authorization": f"token {GH_PAT}", "Accept": "application/vnd.github+json"}

    dispatch(headers, prompt, task_type)
    run = wait_for_completion(headers)

    if run["conclusion"] != "success":
        notify(f"Heavy task failed: {run['conclusion']}")
        sys.exit(1)

    result = fetch_result(headers)
    notify(f"Heavy task done ({task_type})")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
