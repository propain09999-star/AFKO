"""
main.py — orchestrates the radio sweepstakes detector.

For each configured station, runs a loop: capture a short audio chunk
from the live stream -> transcribe it -> check for sweepstakes-related
keywords/patterns -> log any hits. Runs one station per thread so
multiple stations can be monitored concurrently.

Usage:
    python main.py [--config config.yaml]
"""

import argparse
import json
import os
import threading
import time
from datetime import datetime, timezone

import yaml

from capture import capture_loop
from transcribe import transcribe_chunk
from detect import find_hits
from extract import extract_fields


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def process_chunk(wav_path: str, station_cfg: dict, cfg: dict) -> dict:
    """
    Runs one audio chunk through transcribe -> detect -> (optional)
    extract, and returns the same shape log_hit() writes to the log —
    WITHOUT touching the log file or requiring a live stream. This is
    the testable seam: CI/tests can call this directly against a fixed
    WAV file, instead of needing capture_loop() and a real radio stream.

    Returns a dict with "hits": [] when nothing matched (caller decides
    whether to log it) — same hit-detection logic monitor_station uses.
    """
    whisper_binary = cfg["whisper"]["binary_path"]
    whisper_model = cfg["whisper"]["model"]
    keywords = cfg.get("keywords", [])
    regex_patterns = cfg.get("regex_patterns", [])

    transcript = transcribe_chunk(wav_path, whisper_binary, whisper_model)
    hits = find_hits(transcript, keywords, regex_patterns) if transcript else []

    extracted = None
    if hits and cfg.get("extraction", {}).get("enabled"):
        extracted = extract_fields(transcript, cfg["extraction"])

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "station": station_cfg["name"],
        "hits": hits,
        "transcript": transcript,
        "extracted": extracted,
    }


def monitor_station(station_cfg: dict, cfg: dict):
    name = station_cfg["name"]
    stream_url = station_cfg["stream_url"]
    chunk_seconds = station_cfg.get("chunk_seconds", 15)

    tmp_dir = os.path.join(cfg["audio_tmp_dir"], name.replace(" ", "_"))
    log_path = cfg["log_path"]

    print(f"[main] starting monitor for {name}")

    for chunk_path in capture_loop(stream_url, chunk_seconds, tmp_dir):
        entry = process_chunk(chunk_path, station_cfg, cfg)

        # Chunk audio file is no longer needed once transcribed.
        try:
            os.remove(chunk_path)
        except OSError:
            pass

        if entry["hits"]:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            summary = entry["extracted"].get("prize") if entry["extracted"] and "error" not in entry["extracted"] else None
            print(f"[HIT] {name} — {entry['hits']} — {summary or entry['transcript'][:120]}")


def main():
    parser = argparse.ArgumentParser(description="Radio sweepstakes detector")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    stations = cfg.get("stations", [])

    if not stations:
        print("No stations configured in config.yaml — nothing to do.")
        return

    placeholder_stations = [
        s["name"] for s in stations
        if "REPLACE_WITH" in s.get("stream_url", "")
    ]
    if placeholder_stations:
        print(
            "The following stations still have placeholder stream URLs "
            f"in config.yaml and will be skipped: {placeholder_stations}"
        )

    threads = []
    for station_cfg in stations:
        if "REPLACE_WITH" in station_cfg.get("stream_url", ""):
            continue
        t = threading.Thread(target=monitor_station, args=(station_cfg, cfg), daemon=True)
        t.start()
        threads.append(t)

    if not threads:
        print("No stations with a valid stream_url — update config.yaml and rerun.")
        return

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[main] shutting down.")


if __name__ == "__main__":
    main()
