#!/usr/bin/env python3
"""
Runs a heavy task dispatched from TinyLlama via GitHub Actions.
Reads TASK_PAYLOAD env var (JSON), routes to the right handler,
validates strict-JSON output against a schema with retries, and
writes the result to result.json for the workflow to commit back.

Requires: pip install requests jsonschema
Env vars: ANTHROPIC_API_KEY, TASK_PAYLOAD (set by the workflow)
"""
import json
import os
import re
import sys

import requests
import jsonschema

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_RETRIES = 3

# Add/adjust schemas per task_type as your tasks grow
SCHEMAS = {
    "json_extract": {
        "type": "object",
        "properties": {"result": {"type": "object"}},
        "required": ["result"],
    },
}


def call_model(prompt: str, system: str = "") -> str:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": MODEL,
        "max_tokens": 2000,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(ANTHROPIC_URL, headers=headers, json=body, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return "".join(block.get("text", "") for block in data.get("content", []))


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def run_json_task(prompt: str, task_type: str) -> dict:
    schema = SCHEMAS.get(task_type)
    system = (
        "You return ONLY a single valid JSON object. No prose, no markdown "
        "fences, no explanation. If you cannot comply exactly, still return "
        "your best-effort JSON object."
    )
    last_error = None
    output = ""
    for attempt in range(1, MAX_RETRIES + 1):
        retry_note = f"\n\nPrevious attempt failed validation: {last_error}" if last_error else ""
        output = call_model(prompt + retry_note, system=system)
        try:
            parsed = extract_json(output)
            if schema:
                jsonschema.validate(parsed, schema)
            return {"ok": True, "attempts": attempt, "result": parsed}
        except Exception as e:  # noqa: BLE001
            last_error = str(e)
    return {"ok": False, "attempts": MAX_RETRIES, "error": last_error, "raw": output}


def run_code_task(prompt: str) -> dict:
    system = "You write clean, correct, runnable code. Return the code only, in a single fenced block."
    output = call_model(prompt, system=system)
    return {"ok": True, "result": output}


def run_reasoning_task(prompt: str) -> dict:
    output = call_model(prompt)
    return {"ok": True, "result": output}


def main():
    payload = json.loads(os.environ.get("TASK_PAYLOAD", "{}"))
    prompt = payload.get("prompt", "")
    task_type = payload.get("task_type", "reasoning")

    if not prompt:
        print("No prompt provided in payload", file=sys.stderr)
        sys.exit(1)

    if task_type.startswith("json"):
        result = run_json_task(prompt, task_type)
    elif task_type == "code":
        result = run_code_task(prompt)
    else:
        result = run_reasoning_task(prompt)

    with open("result.json", "w") as f:
        json.dump({"task_type": task_type, **result}, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
                   
