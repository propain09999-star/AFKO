#!/usr/bin/env python3
"""AFKO orchestrator entry point.

This file is intentionally small and explicit: it wires together the active AFKO
runtime, the mobile layer, the agent relay, and the optional intelligence layers.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_config() -> dict:
    """Load the unified AFKO configuration.

    For now this is a manifest stub; the practical implementation can be switched to
    a YAML loader once the stack is wired in full.
    """
    return {
        "project": "AFKO",
        "mode": "local-first",
        "integrations": {
            "buzz": True,
            "event_horizon_mobile": True,
            "worldmonitor": True,
            "bittensor": False,
        },
    }


def boot_stack() -> dict:
    config = load_config()
    return {
        "status": "ready",
        "project": config["project"],
        "mode": config["mode"],
        "active_integrations": [
            name for name, enabled in config["integrations"].items() if enabled
        ],
    }


if __name__ == "__main__":
    print(json.dumps(boot_stack(), indent=2))
