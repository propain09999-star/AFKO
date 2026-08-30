"""
extract.py

Post-hit structured-extraction step for radio-sweepstakes-detector.
Runs ONLY when detect.py fires a keyword hit -- not continuously.

This version wires in slm_toolkit.py for reliability against tinyllama's
known weak spots (see slm_toolkit.WEAKNESS_REGISTRY for the full list).

Drop slm_toolkit.py in the same directory (or your shared lib path) and
adjust SCHEMA / FEW_SHOT_PREFIX / field prompts to match your real
transcript format -- the field names below are placeholders matching
what was described (prize, call-to-action style extraction).
"""

import logging
from slm_toolkit import (
    extract_with_retry,
    is_grounded,
    self_consistency_vote,
)

log = logging.getLogger("extract")

# ---------------------------------------------------------------------------
# Schema for the extraction call -- adjust fields to match your real output
# ---------------------------------------------------------------------------
SCHEMA = {
    "type": "object",
    "properties": {
        "is_sweepstakes": {"type": "boolean"},
        "prize_description": {"type": "string"},
        "call_to_action": {"type": "string"},
        "phone_or_code": {"type": "string"},
    },
    "required": ["is_sweepstakes"],
}

# Bias the fallback toward false-positive (flag for human review) rather
# than silently dropping a real hit -- cheap insurance since this only
# runs on keyword-triggered snippets, not continuously.
FALLBACK = {
    "is_sweepstakes": True,
    "prize_description": "unknown",
    "call_to_action": "unknown",
    "phone_or_code": "unknown",
}

# W10 mitigation: explicit negative example so the model doesn't default
# to "yes" on ambiguous/absent mentions.
FEW_SHOT_PREFIX = """Extract sweepstakes details from radio transcript text as JSON.

Example 1:
Text: "Call now, you could win a brand new truck! Dial 555-0199."
Output: {"is_sweepstakes": true, "prize_description": "truck", "call_to_action": "call now", "phone_or_code": "555-0199"}

Example 2:
Text: "Traffic is backed up on the interstate this morning."
Output: {"is_sweepstakes": false, "prize_description": "none", "call_to_action": "none", "phone_or_code": "none"}

Now extract from this text:
"""


def extract(transcript_snippet: str) -> dict:
    """
    Main entry point -- call this from main.py when detect.py fires a hit.
    Returns a dict matching SCHEMA, always -- never raises, never blocks
    the pipeline on a bad model response.
    """
    prompt = FEW_SHOT_PREFIX + f'Text: "{transcript_snippet}"\nOutput:'

    # W1/W9 mitigation: schema-constrained call with retry + truncation handling
    result = extract_with_retry(prompt, SCHEMA, FALLBACK, max_retries=1)

    # W3 mitigation: don't trust free-text fields the model may have invented
    for field in ("prize_description", "call_to_action", "phone_or_code"):
        value = result.get(field, "")
        if value and value.lower() != "none" and not is_grounded(value, transcript_snippet):
            log.warning("Ungrounded field '%s': %r not found in source text", field, value)
            result[field] = "unverified"

    # W4 mitigation: for the binary decision that actually drives whether
    # you send an ntfy.sh alert, don't trust a single low-confidence call --
    # vote across 3 short runs and attach a confidence score.
    if result["is_sweepstakes"]:
        vote_prompt = (
            f'Text: "{transcript_snippet}"\n'
            "Is this genuinely a sweepstakes/prize announcement, not just "
            "background chatter? Answer only 'yes' or 'no'."
        )
        vote, confidence = self_consistency_vote(vote_prompt, n=3)
        result["confidence"] = confidence
        if vote == "no" and confidence >= 0.67:
            # majority of independent votes disagree with the schema call --
            # downgrade rather than silently trusting whichever ran first
            log.info("Self-consistency vote overrode is_sweepstakes -> False (conf=%.2f)", confidence)
            result["is_sweepstakes"] = False
    else:
        result["confidence"] = 1.0  # no vote needed, negative case

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_snippets = [
        "You could win two thousand dollars, just call in during the next ten minutes! Dial 555-0142.",
        "Coming up next, more of your favorite hits on 101.5.",
    ]
    for snippet in test_snippets:
        print(snippet)
        print(extract(snippet))
        print()
  
