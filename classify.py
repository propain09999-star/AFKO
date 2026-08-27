"""
classify.py — asks a local Ollama model what a downloaded file is
about, and gets back a repo slug + short summary + tags.

Same urllib pattern as extract.py in radio-sweepstakes-detector — no
extra HTTP library dependency.
"""

import json
import os
import urllib.request
import urllib.error


CLASSIFY_PROMPT = """You are sorting a downloaded file into a project/topic \
so it can be filed into the right repo.

Filename: {filename}
Content preview (may be empty if not a text file):
\"\"\"{content_preview}\"\"\"

Reply with ONLY a JSON object (no other text, no markdown formatting):
{{
  "slug": "short-lowercase-hyphenated-topic-name",
  "summary": "one sentence describing what this file is",
  "tags": ["tag1", "tag2"]
}}

JSON:"""


def read_text_preview(file_path: str, text_extensions: list, max_chars: int = 2000) -> str:
    """
    Returns the first max_chars of a file's content if it's a
    recognized text extension, otherwise an empty string — classifying
    by filename alone for anything else (PDFs, images, etc. aren't
    extracted here yet).
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in text_extensions:
        return ""
    try:
        with open(file_path, "r", errors="ignore") as f:
            return f.read(max_chars)
    except OSError:
        return ""


def classify_file(file_path: str, cfg: dict) -> dict:
    """
    Returns {"slug": str, "summary": str, "tags": [str]} or
    {"error": str} if the call fails or the response isn't valid JSON.
    Never raises — a classification failure should route the file to
    the pending/manual-review pile, not crash the watch loop.
    """
    filename = os.path.basename(file_path)
    content_preview = read_text_preview(file_path, cfg.get("text_extensions", []))

    prompt = CLASSIFY_PROMPT.format(filename=filename, content_preview=content_preview)

    payload = json.dumps({
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{cfg['ollama_host']}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 60)) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as e:
        return {"error": f"ollama request failed: {e}"}

    raw_output = body.get("response", "").strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.lower().startswith("json"):
            raw_output = raw_output[4:].strip()

    try:
        result = json.loads(raw_output)
    except json.JSONDecodeError:
        return {"error": "model did not return valid JSON", "raw_output": raw_output}

    # Minimal sanity check — a slug with spaces/uppercase isn't
    # usable as a directory/repo name, and this is easy to catch
    # before it becomes a filesystem problem downstream
    slug = result.get("slug", "")
    if not slug or not all(c.islower() or c.isdigit() or c == "-" for c in slug):
        return {"error": f"model returned an unusable slug: {slug!r}", "raw_output": raw_output}

    return result
