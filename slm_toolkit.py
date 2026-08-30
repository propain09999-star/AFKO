"""
slm_toolkit.py

A reusable set of patterns for getting reliable structured output out of a
weak local model (tinyllama via Ollama). Built to drop into projects like
radio-sweepstakes-detector/extract.py or repo-curator's classification step.

Covers the failure modes small models hit most:
  1. Invalid / malformed JSON
  2. Multi-field extraction accuracy collapse
  3. Hallucinated fields not present in the source text
  4. Overconfident wrong answers with no way to detect them
  5. Prompt drift on long inputs

Requires: `requests` (or swap for the ollama python client if you use that)
"""

import json
import re
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "tinyllama"


# ---------------------------------------------------------------------------
# 1. Schema-constrained generation
# ---------------------------------------------------------------------------
# Ollama supports a `format` field that accepts a JSON schema. This forces
# grammar-constrained decoding -- the model literally cannot emit a token
# that would produce invalid JSON. This fixes ~80% of "strict JSON" failures
# on its own, because malformed JSON is a decoding problem, not a prompting
# problem.

def call_ollama_structured(prompt: str, schema: dict, temperature: float = 0.0) -> dict:
    """Call Ollama with a JSON schema constraint. Returns parsed dict or raises."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "format": schema,          # <-- the key line
        "stream": False,
        "options": {"temperature": temperature},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    raw_text = resp.json()["response"]
    return json.loads(raw_text)    # should already be valid due to format=schema


# ---------------------------------------------------------------------------
# 2. Cleanup layer -- for when you're not using schema mode, or the model
#    wraps output in markdown/commentary anyway (tinyllama does this often)
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_TRAILING_JUNK_RE = re.compile(r"^[^{\[]*")   # strip any preamble before { or [

def strip_to_json(text: str) -> str:
    """Remove markdown fences and leading chatter before the JSON starts."""
    text = _FENCE_RE.sub("", text).strip()
    text = _TRAILING_JUNK_RE.sub("", text, count=1)
    # trim anything after the last closing brace/bracket
    last_close = max(text.rfind("}"), text.rfind("]"))
    if last_close != -1:
        text = text[: last_close + 1]
    return text.strip()


# ---------------------------------------------------------------------------
# 3. Retry-with-repair loop
# ---------------------------------------------------------------------------
# tinyllama rarely self-corrects past one retry, so we cap it hard and fall
# back to a safe default rather than looping and burning time/battery.

REPAIR_HINT = (
    "\n\nYour previous output was not valid JSON. "
    "Respond with ONLY valid JSON matching the schema. No commentary, no markdown."
)

def extract_with_retry(prompt: str, schema: dict, fallback: dict, max_retries: int = 1) -> dict:
    attempt_prompt = prompt
    for attempt in range(max_retries + 1):
        try:
            raw = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": attempt_prompt,
                    "stream": False,
                    "options": {"temperature": 0.0},
                },
                timeout=60,
            ).json()["response"]
            cleaned = strip_to_json(raw)
            data = json.loads(cleaned)
            if _matches_schema(data, schema):
                return data
        except (json.JSONDecodeError, requests.RequestException):
            pass
        attempt_prompt = prompt + REPAIR_HINT
    return fallback  # give up cleanly rather than looping forever


def _matches_schema(data: dict, schema: dict) -> bool:
    """Cheap structural check -- required keys present, right coarse types."""
    required = schema.get("required", [])
    props = schema.get("properties", {})
    if not all(k in data for k in required):
        return False
    type_map = {"string": str, "number": (int, float), "boolean": bool,
                "array": list, "object": dict}
    for key, spec in props.items():
        if key in data and "type" in spec:
            expected = type_map.get(spec["type"])
            if expected and not isinstance(data[key], expected):
                return False
    return True


# ---------------------------------------------------------------------------
# 4. Task decomposition -- one field/decision per call
# ---------------------------------------------------------------------------
# Multi-field extraction is where tinyllama's per-field accuracy compounds
# into near-zero all-fields-correct accuracy. Splitting into one call per
# field trades latency for reliability -- worth it for a low-frequency,
# hit-triggered pipeline like extract.py.

def extract_fields_separately(text: str, field_prompts: dict, fallback_value=None) -> dict:
    """
    field_prompts: {"prize_amount": "What dollar amount is mentioned, if any?
                     Respond with ONLY the number or 'none'.", ...}
    Returns dict of field -> raw string answer (caller decides how to coerce types).
    """
    results = {}
    for field, instruction in field_prompts.items():
        prompt = f"Text: {text}\n\n{instruction}"
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.0}},
            timeout=30,
        ).json()["response"].strip()
        results[field] = resp if resp else fallback_value
    return results


# ---------------------------------------------------------------------------
# 5. Grounding check -- catch hallucinated fields
# ---------------------------------------------------------------------------
# Small models will happily invent a phone number or prize name that isn't
# in the source text. Cheap fix: after extraction, verify extracted string
# values actually appear (fuzzy) in the source before trusting them.

def is_grounded(value: str, source_text: str, min_overlap: float = 0.5) -> bool:
    """Rough check that extracted value's words actually appear in source."""
    if not value or not isinstance(value, str):
        return False
    value_words = set(re.findall(r"\w+", value.lower()))
    source_words = set(re.findall(r"\w+", source_text.lower()))
    if not value_words:
        return False
    overlap = len(value_words & source_words) / len(value_words)
    return overlap >= min_overlap


# ---------------------------------------------------------------------------
# 6. Confidence gating via self-consistency
# ---------------------------------------------------------------------------
# For a binary/low-cardinality decision (keyword hit -> real sweepstakes
# mention: yes/no), run the same prompt 3x at low temperature and take
# majority vote. Cheap way to get a confidence signal out of a model that
# can't reliably self-report confidence in its own answer.

def self_consistency_vote(prompt: str, n: int = 3, temperature: float = 0.3) -> tuple[str, float]:
    votes = []
    for _ in range(n):
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": temperature}},
            timeout=30,
        ).json()["response"].strip().lower()
        votes.append(resp)
    winner = max(set(votes), key=votes.count)
    confidence = votes.count(winner) / n
    return winner, confidence


# ---------------------------------------------------------------------------
# Example: wiring these together for a sweepstakes-detector-style extraction
# ---------------------------------------------------------------------------

EXAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_sweepstakes": {"type": "boolean"},
        "prize_description": {"type": "string"},
        "call_to_action": {"type": "string"},
    },
    "required": ["is_sweepstakes"],
}

EXAMPLE_FALLBACK = {
    "is_sweepstakes": True,   # bias toward false-positive over silent drop
    "prize_description": "unknown",
    "call_to_action": "unknown",
}

FEW_SHOT_PREFIX = """Extract sweepstakes details from radio transcript text as JSON.

Example 1:
Text: "Call now, you could win a brand new truck!"
Output: {"is_sweepstakes": true, "prize_description": "truck", "call_to_action": "call now"}

Example 2:
Text: "Traffic is backed up on the interstate this morning."
Output: {"is_sweepstakes": false, "prize_description": "none", "call_to_action": "none"}

Now extract from this text:
"""

def extract_sweepstakes_details(transcript_snippet: str) -> dict:
    prompt = FEW_SHOT_PREFIX + f'Text: "{transcript_snippet}"\nOutput:'
    result = extract_with_retry(prompt, EXAMPLE_SCHEMA, EXAMPLE_FALLBACK, max_retries=1)

    # ground-check the free-text fields against the source
    for field in ("prize_description", "call_to_action"):
        if field in result and not is_grounded(result[field], transcript_snippet):
            result[field] = "unverified"

    return result


if __name__ == "__main__":
    test_text = "You could win two thousand dollars, just call in during the next ten minutes!"
    print(extract_sweepstakes_details(test_text))
  
