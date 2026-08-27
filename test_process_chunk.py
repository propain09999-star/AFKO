"""
tests/test_process_chunk.py

Tests main.py's process_chunk() — the seam extracted specifically so
this doesn't need a live stream, a real whisper.cpp binary, or a
running Ollama instance. transcribe_chunk/find_hits/extract_fields
are mocked; this tests the SHAPE and LOGIC of what process_chunk
returns, not the actual transcription/extraction quality.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import main  # noqa: E402


BASE_CFG = {
    "whisper": {"binary_path": "whisper-cli", "model": "base.en"},
    "keywords": ["sweepstakes", "win a"],
    "regex_patterns": [r"\$[0-9][0-9,]*"],
    "extraction": {
        "enabled": True,
        "model": "qwen2.5:1.5b",
        "ollama_host": "http://localhost:11434",
        "timeout_seconds": 60,
    },
}
STATION_CFG = {"name": "Test Station"}


def test_no_hit_skips_extraction():
    """A transcript with no keyword/regex match should never call extract_fields."""
    with patch("main.transcribe_chunk", return_value="just some regular radio chatter"), \
         patch("main.find_hits", return_value=[]), \
         patch("main.extract_fields") as mock_extract:

        entry = main.process_chunk("fake.wav", STATION_CFG, BASE_CFG)

        assert entry["hits"] == []
        assert entry["extracted"] is None
        mock_extract.assert_not_called()  # this is the actual bug class we care about:
        # extraction silently running (and costing time/resources) on a non-hit


def test_hit_triggers_extraction_when_enabled():
    with patch("main.transcribe_chunk", return_value="you could win a cash prize, call now"), \
         patch("main.find_hits", return_value=["win a"]), \
         patch("main.extract_fields", return_value={"prize": "cash prize", "sponsor": None,
                                                       "prize_amount": None, "entry_method": "call",
                                                       "contact_info": None, "deadline": None}) as mock_extract:

        entry = main.process_chunk("fake.wav", STATION_CFG, BASE_CFG)

        assert entry["hits"] == ["win a"]
        assert entry["extracted"]["prize"] == "cash prize"
        mock_extract.assert_called_once()


def test_hit_skips_extraction_when_disabled_in_config():
    cfg = {**BASE_CFG, "extraction": {"enabled": False}}
    with patch("main.transcribe_chunk", return_value="win a trip today"), \
         patch("main.find_hits", return_value=["win a"]), \
         patch("main.extract_fields") as mock_extract:

        entry = main.process_chunk("fake.wav", STATION_CFG, cfg)

        assert entry["hits"] == ["win a"]
        assert entry["extracted"] is None
        mock_extract.assert_not_called()


def test_empty_transcript_produces_no_hits():
    """transcribe_chunk returning '' (its documented failure mode) must not crash
    or somehow still produce a hit — find_hits should never even be asked."""
    with patch("main.transcribe_chunk", return_value=""), \
         patch("main.find_hits") as mock_find_hits:

        entry = main.process_chunk("fake.wav", STATION_CFG, BASE_CFG)

        assert entry["hits"] == []
        assert entry["transcript"] == ""
        mock_find_hits.assert_not_called()


def test_extraction_error_is_preserved_not_dropped():
    """If extract_fields returns an {"error": ...} dict, process_chunk must not
    swallow it — the hit should still be logged with the error visible."""
    with patch("main.transcribe_chunk", return_value="call now to win a prize"), \
         patch("main.find_hits", return_value=["call now"]), \
         patch("main.extract_fields", return_value={"error": "ollama request failed: timeout"}):

        entry = main.process_chunk("fake.wav", STATION_CFG, BASE_CFG)

        assert entry["hits"] == ["call now"]
        assert entry["extracted"] == {"error": "ollama request failed: timeout"}
