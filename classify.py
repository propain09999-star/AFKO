#!/usr/bin/env python3
"""
classify.py -- ask a local Ollama model to classify a piece of text
into a repo slug + short summary + tags.

No classes. Just functions. Import classify_text() from other scripts.
"""

import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "tinyllama"

PROMPT_TEMPLATE = """You are sorting a file into a project repo.

Existing repos: {existing_repos}

File name: {filename}
File content (truncated):
---
{content}
---

Reply with ONLY a JSON object, no other text, in this exact shape:
{{"repo_slug": "short-kebab-case-name", "summary": "one sentence summary", "tags": ["tag1", "tag2"], "is_existing": true or false}}

If the file clearly belongs to one of the existing repos, set is_existing to true
and repo_slug to that repo's exact name. Otherwise pick a new short kebab-case slug
and set is_existing to false.
"""


def _extract_json(text):
    """Ollama sometimes wraps JSON in extra text -- pull out the first {...} block."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def classify_text(filename, content, existing_repos, model=MODEL, url=OLLAMA_URL, timeout=300):
    """Returns dict: {repo_slug, summary, tags, is_existing} or None on failure."""
    truncated = content[:4000]  # keep it well under tinyllama's context window
    prompt = PROMPT_TEMPLATE.format(
        existing_repos=", ".join(existing_repos) if existing_repos else "(none yet)",
        filename=filename,
        content=truncated,
    )

    resp = requests.post(
        url,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "")

    result = _extract_json(raw)
    if result is None:
        return None

    # sanitize the slug regardless of what the model gave us
    slug = result.get("repo_slug", "unsorted")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-") or "unsorted"
    result["repo_slug"] = slug
    result.setdefault("summary", "")
    result.setdefault("tags", [])
    result.setdefault("is_existing", slug in existing_repos)
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: classify.py <file>")
        sys.exit(1)

    with open(sys.argv[1], "r", errors="ignore") as f:
        text = f.read()

    out = classify_text(sys.argv[1], text, existing_repos=[])
    print(json.dumps(out, indent=2))
  
