#!/usr/bin/env python3
"""Tests for skills/daily-papers/extract_affiliations.py.

Run:
    python3 scripts/test_extract_affiliations.py
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE_DIR = REPO / "skills" / "daily-papers"
SHARED_DIR = REPO / "skills" / "_shared"

for d in (str(MODULE_DIR), str(SHARED_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)

import extract_affiliations as mod


# ── extract_header ──────────────────────────────────────────────────────────

def test_extract_header_stops_at_abstract():
    text = "Title\nAuthor\nUniversity of X\n\nAbstract\nBody text here."
    header = mod.extract_header(text)
    assert "Body text" not in header
    assert "University of X" in header


def test_extract_header_stops_at_introduction():
    text = "\n".join(["Title", "Author", "Affil"] + ["filler"] * 5 + ["1. Introduction", "Paragraph"])
    header = mod.extract_header(text)
    assert "Paragraph" not in header


def test_extract_header_max_80_lines():
    text = "\n".join([f"line {i}" for i in range(100)])
    header = mod.extract_header(text)
    assert header.count("\n") <= 82


# ── is_noise ────────────────────────────────────────────────────────────────

def test_noise_short_line():
    assert mod.is_noise("ab") is True


def test_noise_email():
    assert mod.is_noise("alice@example.com") is True


def test_noise_url():
    assert mod.is_noise("https://arxiv.org/abs/2301.00001") is True


def test_noise_arxiv_id():
    assert mod.is_noise("2301.12345") is True


def test_noise_numbers_only():
    assert mod.is_noise("1, 2, 3") is True


def test_not_noise_institution():
    assert mod.is_noise("Tsinghua University") is False


def test_noise_keywords_line():
    assert mod.is_noise("Keywords: speech synthesis, TTS") is True


# ── looks_like_sentence ─────────────────────────────────────────────────────

def test_sentence_starts_with_we():
    assert mod.looks_like_sentence("We propose a novel method for speech synthesis") is True


def test_sentence_multiple_periods():
    assert mod.looks_like_sentence("First point. Second point. Third point.") is True


def test_not_sentence_institution():
    assert mod.looks_like_sentence("University of California, Berkeley") is False


def test_not_sentence_short_proper_nouns():
    assert mod.looks_like_sentence("Microsoft Research Asia") is False


# ── has_inst_keyword ────────────────────────────────────────────────────────

def test_has_keyword_university():
    assert mod.has_inst_keyword("Tsinghua University") is True


def test_has_keyword_lab():
    assert mod.has_inst_keyword("Google DeepMind") is True


def test_no_keyword():
    assert mod.has_inst_keyword("some random text") is False


def test_boundary_keyword_intel():
    assert mod.has_inst_keyword("Intel Labs") is True
    assert mod.has_inst_keyword("intelligence research") is False


# ── clean_affiliation ───────────────────────────────────────────────────────

def test_clean_removes_footnote_markers():
    assert mod.clean_affiliation("1,2 University of Oxford") == "University of Oxford"


def test_clean_removes_trailing_markers():
    assert mod.clean_affiliation("MIT †") == "MIT"


def test_clean_removes_braces():
    assert mod.clean_affiliation("{Stanford University}") == "Stanford University"


def test_clean_removes_intern_suffix():
    assert mod.clean_affiliation("ByteDance Intern") == "ByteDance"


# ── split_numbered_affiliations ─────────────────────────────────────────────

def test_split_comma_separated():
    result = mod.split_numbered_affiliations("1 Foo University, 2 Bar Institute, 3 Baz Lab")
    assert len(result) == 3


def test_split_space_separated():
    result = mod.split_numbered_affiliations("University of A 2 Nvidia 3 Amazon")
    assert len(result) == 3


def test_no_split_single():
    result = mod.split_numbered_affiliations("Stanford University")
    assert result == ["Stanford University"]


# ── _is_author_line ─────────────────────────────────────────────────────────

def test_author_line_comma_names():
    assert mod._is_author_line("Alice Smith, Bob Jones, Charlie Lee") is True


def test_author_line_space_names():
    assert mod._is_author_line("Alice Smith Bob Jones Charlie Lee David Wang") is True


def test_not_author_short_institution():
    assert mod._is_author_line("Frontier Robotics") is False


def test_not_author_numbered():
    assert mod._is_author_line("1 University of Tokyo") is False


# ── extract_affiliations (integration) ──────────────────────────────────────

def test_extract_basic():
    text = """CosyVoice: A Scalable Multilingual TTS Model
Alice Zhang, Bob Li, Charlie Wang
Alibaba Group, Tongyi Lab
Department of Computer Science, Tsinghua University

Abstract
We present CosyVoice, a multilingual TTS system.
"""
    affs = mod.extract_affiliations(text)
    assert any("alibaba" in a.lower() or "tongyi" in a.lower() for a in affs), f"Expected Alibaba/Tongyi in {affs}"
    assert any("tsinghua" in a.lower() for a in affs), f"Expected Tsinghua in {affs}"


def test_extract_dedup_substrings():
    text = """Title
Author
Microsoft Research
Microsoft Research Asia

Abstract
Body
"""
    affs = mod.extract_affiliations(text)
    ms_affs = [a for a in affs if "microsoft" in a.lower()]
    assert len(ms_affs) <= 1, f"Expected dedup, got {ms_affs}"


def test_extract_empty_text():
    affs = mod.extract_affiliations("")
    assert affs == []


def test_extract_no_affiliations():
    text = """Some Random Title
By someone
This is just body text with no institutions mentioned.

Abstract
More body text here.
"""
    affs = mod.extract_affiliations(text)
    assert isinstance(affs, list)


# ── Runner ──────────────────────────────────────────────────────────────────

TESTS = [
    test_extract_header_stops_at_abstract,
    test_extract_header_stops_at_introduction,
    test_extract_header_max_80_lines,
    test_noise_short_line,
    test_noise_email,
    test_noise_url,
    test_noise_arxiv_id,
    test_noise_numbers_only,
    test_not_noise_institution,
    test_noise_keywords_line,
    test_sentence_starts_with_we,
    test_sentence_multiple_periods,
    test_not_sentence_institution,
    test_not_sentence_short_proper_nouns,
    test_has_keyword_university,
    test_has_keyword_lab,
    test_no_keyword,
    test_boundary_keyword_intel,
    test_clean_removes_footnote_markers,
    test_clean_removes_trailing_markers,
    test_clean_removes_braces,
    test_clean_removes_intern_suffix,
    test_split_comma_separated,
    test_split_space_separated,
    test_no_split_single,
    test_author_line_comma_names,
    test_author_line_space_names,
    test_not_author_short_institution,
    test_not_author_numbered,
    test_extract_basic,
    test_extract_dedup_substrings,
    test_extract_empty_text,
    test_extract_no_affiliations,
]

if __name__ == "__main__":
    passed = failed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except (AssertionError, Exception) as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1
    print(f"\n{passed} / {passed + failed} passed")
    sys.exit(0 if failed == 0 else 1)
