#!/usr/bin/env python3
"""Tests for daily-papers-notes/backfill_links.py (P2-7).

Covers: extract_method_name_from_title, match_papers_with_notes,
backfill_links, update_diversion_table.

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_backfill_links.py
"""

import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
BACKFILL_PY = REPO / "skills" / "daily-papers-notes" / "backfill_links.py"


def _import_backfill():
    spec = importlib.util.spec_from_file_location("backfill_links", BACKFILL_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLE_RECOMMENDATION = """\
---
date: 2026-05-21
---

# 2026-05-21 论文推荐

## 分流表

| # | 方法名 | 分类建议 |
|---|--------|----------|
| 1 | [[CosyVoice]] | TTS |
| 2 | [[NewMethod]] | ASR |

---

### 1. CosyVoice: Scalable Multilingual TTS

- **来源**: arXiv 2405.12345
- **分数**: 8

### 2. NewMethod: A Novel Approach to ASR

- **来源**: arXiv 2405.67890
- **分数**: 6

### 3. UnknownPaper: Something Else

- **来源**: arXiv 2405.11111
- **分数**: 4
"""


def _make_notes_index():
    """Simulated notes_index as scan_notes() would return."""
    mod = _import_backfill()
    return {
        mod._normalize_name("CosyVoice"): {"name": "CosyVoice", "path": Path("论文笔记/1-TTS/CosyVoice.md")},
        mod._normalize_name("F5-TTS"): {"name": "F5-TTS", "path": Path("论文笔记/1-TTS/F5-TTS.md")},
    }


# ── extract_method_name_from_title ────────────────────────────────────────


def test_extract_method_name_colon():
    mod = _import_backfill()
    assert mod.extract_method_name_from_title("CosyVoice: Scalable TTS") == "CosyVoice"


def test_extract_method_name_no_colon():
    mod = _import_backfill()
    result = mod.extract_method_name_from_title("SomePaper A Novel Approach")
    assert result == "SomePaper"


def test_extract_method_name_with_number_prefix():
    mod = _import_backfill()
    assert mod.extract_method_name_from_title("1. NavThinker: Action") == "NavThinker"


def test_extract_method_name_empty():
    mod = _import_backfill()
    assert mod.extract_method_name_from_title("") == ""


# ── match_papers_with_notes ───────────────────────────────────────────────


def test_match_finds_existing_note():
    mod = _import_backfill()
    notes_index = _make_notes_index()
    matches = mod.match_papers_with_notes(SAMPLE_RECOMMENDATION, notes_index)
    method_names = [m["method_name"] for m in matches]
    assert "CosyVoice" in method_names


def test_match_skips_unknown():
    """Papers without matching notes are not in matches."""
    mod = _import_backfill()
    notes_index = _make_notes_index()
    matches = mod.match_papers_with_notes(SAMPLE_RECOMMENDATION, notes_index)
    method_names = [m["method_name"] for m in matches]
    assert "NewMethod" not in method_names
    assert "UnknownPaper" not in method_names


def test_match_skips_already_linked():
    """Papers that already have a 笔记 link are skipped."""
    mod = _import_backfill()
    notes_index = _make_notes_index()
    content_with_link = SAMPLE_RECOMMENDATION.replace(
        "- **来源**: arXiv 2405.12345\n- **分数**: 8",
        "- **来源**: arXiv 2405.12345\n- 📒 **笔记**: [[CosyVoice]]\n- **分数**: 8",
    )
    matches = mod.match_papers_with_notes(content_with_link, notes_index)
    assert len(matches) == 0


def test_match_uses_normalized_names():
    """Matching works with different casing/punctuation in note names."""
    mod = _import_backfill()
    # F5-TTS note exists; paper title has "F5-TTS"
    content = """\
### 1. F5-TTS: A Diffusion-based TTS System

- **来源**: arXiv 2405.99999
- **分数**: 7
"""
    notes_index = _make_notes_index()
    matches = mod.match_papers_with_notes(content, notes_index)
    assert len(matches) == 1
    assert matches[0]["note_name"] == "F5-TTS"


# ── backfill_links ────────────────────────────────────────────────────────


def test_backfill_inserts_link():
    """backfill_links inserts note link after 来源 line."""
    mod = _import_backfill()
    notes_index = _make_notes_index()
    tmp = Path(tempfile.mktemp(suffix=".md"))
    tmp.write_text(SAMPLE_RECOMMENDATION, encoding="utf-8")

    count = mod.backfill_links(tmp, notes_index)
    result = tmp.read_text(encoding="utf-8")

    assert count == 1
    assert "- 📒 **笔记**: [[CosyVoice]]" in result
    # Verify it's after the 来源 line
    source_pos = result.find("- **来源**: arXiv 2405.12345")
    note_pos = result.find("- 📒 **笔记**: [[CosyVoice]]")
    assert note_pos > source_pos


def test_backfill_returns_zero_no_matches():
    mod = _import_backfill()
    notes_index = {}  # empty index
    tmp = Path(tempfile.mktemp(suffix=".md"))
    tmp.write_text(SAMPLE_RECOMMENDATION, encoding="utf-8")
    count = mod.backfill_links(tmp, notes_index)
    assert count == 0


# ── update_diversion_table ────────────────────────────────────────────────


def test_diversion_table_updates_wikilink():
    """When method_name != note_name (after normalize), wikilink in 分流表 is updated."""
    mod = _import_backfill()
    # "WavFlow" (from paper title) vs "WavFlow-v2" (actual note filename)
    # These normalize differently: "wavflow" vs "wavflowv2"
    content = """\
## 分流表

| # | 方法名 |
|---|--------|
| 1 | [[WavFlow]] |

## 正文

### 1. WavFlow: Audio Generation

- **来源**: arXiv 2405.00001
- 📒 **笔记**: [[WavFlow-v2]]
"""
    tmp = Path(tempfile.mktemp(suffix=".md"))
    tmp.write_text(content, encoding="utf-8")

    matches = [{
        "method_name": "WavFlow",
        "note_name": "WavFlow-v2",
        "section_start": 0,
        "source_line_end": 0,
    }]
    notes_index = {}

    mod.update_diversion_table(tmp, notes_index, matches)
    result = tmp.read_text(encoding="utf-8")
    assert "[[WavFlow-v2]]" in result
    assert "[[WavFlow]]" not in result.split("## 分流表")[1].split("## 正文")[0]


# ── Runner ────────────────────────────────────────────────────────────────

TESTS = [
    test_extract_method_name_colon,
    test_extract_method_name_no_colon,
    test_extract_method_name_with_number_prefix,
    test_extract_method_name_empty,
    test_match_finds_existing_note,
    test_match_skips_unknown,
    test_match_skips_already_linked,
    test_match_uses_normalized_names,
    test_backfill_inserts_link,
    test_backfill_returns_zero_no_matches,
    test_diversion_table_updates_wikilink,
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
