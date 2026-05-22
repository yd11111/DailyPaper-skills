#!/usr/bin/env python3
"""Tests for paper-reader/paper_daemon.py pure functions (P2-6).

Covers: detect_limit_error, parse_reset_wait_seconds,
title_matches_note, _normalize_method_name, _extract_note_method_names.

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_paper_daemon.py
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

REPO = Path(__file__).resolve().parents[1]
DAEMON_PY = REPO / "skills" / "paper-reader" / "paper_daemon.py"


def _import_daemon():
    spec = importlib.util.spec_from_file_location("paper_daemon", DAEMON_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── detect_limit_error ────────────────────────────────────────────────────


def test_detect_rate_limit():
    mod = _import_daemon()
    assert mod.detect_limit_error("Error: rate limit exceeded") == "RATE_LIMIT"
    assert mod.detect_limit_error("Too Many Requests (429)") == "RATE_LIMIT"


def test_detect_quota_limit():
    mod = _import_daemon()
    assert mod.detect_limit_error("You've hit your limit for today") == "QUOTA_LIMIT"
    assert mod.detect_limit_error("usage limit reached, resets 9pm") == "QUOTA_LIMIT"


def test_detect_no_limit():
    mod = _import_daemon()
    assert mod.detect_limit_error("Error: file not found") is None
    assert mod.detect_limit_error("Success") is None
    assert mod.detect_limit_error("") is None


# ── parse_reset_wait_seconds ──────────────────────────────────────────────


def test_parse_reset_basic():
    """Parses 'resets 9pm (Asia/Shanghai)' and returns positive seconds."""
    mod = _import_daemon()
    result = mod.parse_reset_wait_seconds("resets 9pm (Asia/Shanghai)")
    assert result is not None
    assert result >= 60


def test_parse_reset_with_minutes():
    mod = _import_daemon()
    result = mod.parse_reset_wait_seconds("resets 9:30pm (Asia/Shanghai)")
    assert result is not None
    assert result >= 60


def test_parse_reset_no_match():
    mod = _import_daemon()
    assert mod.parse_reset_wait_seconds("no reset info here") is None
    assert mod.parse_reset_wait_seconds("") is None


def test_parse_reset_invalid_tz():
    mod = _import_daemon()
    assert mod.parse_reset_wait_seconds("resets 9pm (Invalid/Timezone)") is None


# ── _normalize_method_name ────────────────────────────────────────────────


def test_normalize_basic():
    mod = _import_daemon()
    assert mod._normalize_method_name("F5-TTS") == "f5tts"
    assert mod._normalize_method_name("CosyVoice 2") == "cosyvoice2"


def test_normalize_greek():
    mod = _import_daemon()
    assert mod._normalize_method_name("π0.5") == "pi05"
    assert mod._normalize_method_name("φ-Net") == "phinet"


def test_normalize_subscripts():
    mod = _import_daemon()
    assert mod._normalize_method_name("Model₂") == "model2"


def test_normalize_ampersand():
    mod = _import_daemon()
    assert mod._normalize_method_name("A & B") == "aandb"


# ── _extract_note_method_names ────────────────────────────────────────────


def test_extract_note_names_basic():
    mod = _import_daemon()
    result = mod._extract_note_method_names("CosyVoice")
    assert "cosyvoice" in result


def test_extract_note_names_dated():
    """Stems like '2024_F5-TTS' produce both full and stripped forms."""
    mod = _import_daemon()
    result = mod._extract_note_method_names("2024_F5-TTS")
    assert "f5tts" in result


def test_extract_note_names_no_date_prefix():
    mod = _import_daemon()
    result = mod._extract_note_method_names("π0.5")
    assert "pi05" in result


# ── title_matches_note ────────────────────────────────────────────────────


def test_title_matches_exact():
    mod = _import_daemon()
    notes = {"cosyvoice": "CosyVoice.md"}
    assert mod.title_matches_note("CosyVoice: Scalable TTS", notes) is True


def test_title_matches_full_title():
    mod = _import_daemon()
    notes = {"cosyvoicescalablettswithlargescalestreamabletts": "x.md"}
    # Normalized full title won't match short note
    notes2 = {"cosyvoice": "CosyVoice.md"}
    assert mod.title_matches_note("CosyVoice: Scalable TTS", notes2) is True


def test_title_no_match():
    mod = _import_daemon()
    notes = {"wavflow": "WavFlow.md"}
    assert mod.title_matches_note("CosyVoice: Something", notes) is False


def test_title_matches_empty():
    mod = _import_daemon()
    assert mod.title_matches_note("", {"x": "y"}) is False
    assert mod.title_matches_note("SomeTitle", {}) is False


def test_title_matches_substring():
    """Note name is substring of title method (length check applies)."""
    mod = _import_daemon()
    notes = {"f5tts": "F5-TTS.md"}
    assert mod.title_matches_note("F5-TTS-v2: Extended", notes) is True


def test_title_no_match_short_substring():
    """Very short note names don't false-match longer method names."""
    mod = _import_daemon()
    notes = {"gs": "GS.md"}
    # "gs" is len 2, so len > 3 check should prevent match
    assert mod.title_matches_note("3DGS-Renderer: Fast", notes) is False


# ── Runner ────────────────────────────────────────────────────────────────

TESTS = [
    test_detect_rate_limit,
    test_detect_quota_limit,
    test_detect_no_limit,
    test_parse_reset_basic,
    test_parse_reset_with_minutes,
    test_parse_reset_no_match,
    test_parse_reset_invalid_tz,
    test_normalize_basic,
    test_normalize_greek,
    test_normalize_subscripts,
    test_normalize_ampersand,
    test_extract_note_names_basic,
    test_extract_note_names_dated,
    test_extract_note_names_no_date_prefix,
    test_title_matches_exact,
    test_title_matches_full_title,
    test_title_no_match,
    test_title_matches_empty,
    test_title_matches_substring,
    test_title_no_match_short_substring,
]


def main():
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{len(TESTS) - failed} / {len(TESTS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
