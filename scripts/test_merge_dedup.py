#!/usr/bin/env python3
"""Tests for fetch_and_score.merge_and_dedup (P1-5).

Covers: age filter, merge-by-id, history dedup, min_score, backfill, top_n cap.

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_merge_dedup.py
"""

import importlib.util
import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
FETCH_PY = REPO / "skills" / "daily-papers" / "fetch_and_score.py"


def _import_fetch():
    spec = importlib.util.spec_from_file_location("fetch_and_score", FETCH_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_paper(arxiv_id: str, pub_date: str, score: int, source: str = "hf") -> dict:
    return {
        "title": f"Paper {arxiv_id}",
        "abstract": "test abstract",
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
        "date": pub_date,
        "score": score,
        "source": source,
        "category": "",
    }


TODAY = date(2026, 5, 21)


def _call_merge(mod, hf=None, arxiv=None, target=TODAY, days=1, top_n=30,
                history=None, max_age=7, min_score=1, dailypapers_dir=None):
    """Helper: patch constants, write temp history, call merge_and_dedup."""
    tmp = Path(tempfile.mkdtemp())
    hist_path = tmp / ".history.json"
    hist_path.write_text(json.dumps(history or []))
    dp_dir = Path(dailypapers_dir) if dailypapers_dir else tmp

    patches = {
        "HISTORY_PATH": hist_path,
        "DAILYPAPERS_DIR": dp_dir,
        "MAX_AGE_DAYS": max_age,
        "MIN_SCORE": min_score,
        "TOP_N": top_n,
    }
    with patch.multiple(mod, **patches):
        result = mod.merge_and_dedup(
            hf or [], arxiv or [], target, days=days, top_n=top_n,
        )
    return result


# ── Tests ─────────────────────────────────────────────────────────────────


def test_age_filter_drops_old():
    """Papers older than MAX_AGE_DAYS are dropped."""
    mod = _import_fetch()
    old_date = (TODAY - timedelta(days=30)).isoformat()
    papers = [make_paper("2605.00001", old_date, score=5)]
    top, stats = _call_merge(mod, hf=papers, max_age=7)
    assert len(top) == 0, f"expected 0 papers, got {len(top)}"
    assert stats["filter_steps"]["age_filter"]["dropped_aged"] == 1


def test_age_filter_keeps_recent():
    """Papers within MAX_AGE_DAYS are kept."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=2)).isoformat()
    papers = [make_paper("2605.00002", recent, score=5)]
    top, stats = _call_merge(mod, hf=papers, max_age=7)
    assert len(top) == 1
    assert stats["filter_steps"]["age_filter"]["dropped_aged"] == 0


def test_age_filter_no_date_passes():
    """Papers with empty date are not dropped."""
    mod = _import_fetch()
    papers = [make_paper("2605.00003", "", score=5)]
    top, stats = _call_merge(mod, hf=papers, max_age=7)
    assert len(top) == 1


def test_merge_keeps_higher_score():
    """Same arxiv_id in both sources → keep the one with higher score."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=1)).isoformat()
    hf = [make_paper("2605.00004", recent, score=3)]
    arxiv = [make_paper("2605.00004", recent, score=7)]
    top, stats = _call_merge(mod, hf=hf, arxiv=arxiv, max_age=7)
    assert len(top) == 1
    assert top[0]["score"] == 7


def test_history_dedup_removes_seen():
    """Papers already in history are removed in single-day mode."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=1)).isoformat()
    # Need 20+ new papers so backfill doesn't re-add the deduped one
    papers = [make_paper(f"2605.4{i:04d}", recent, score=5) for i in range(21)]
    papers.append(make_paper("2605.00005", recent, score=5))
    history = [
        {"id": "2605.00005", "date": "2026-05-19", "title": "Old"},
        *[{"id": f"2600.{i:05d}", "date": "2026-01-01", "title": "x"} for i in range(10)],
    ]
    top, stats = _call_merge(mod, hf=papers, history=history)
    ids = [p["url"].split("/")[-1] for p in top]
    assert "2605.00005" not in ids, "history paper should be deduped"
    assert stats["filter_steps"]["history_dedup"]["removed_already_recommended"] == 1


def test_history_dedup_skipped_multiday():
    """In multi-day mode (days>1), history dedup is skipped."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=1)).isoformat()
    papers = [make_paper("2605.00007", recent, score=5)]
    history = [
        {"id": "2605.00007", "date": "2026-05-19", "title": "Old"},
        *[{"id": f"2600.{i:05d}", "date": "2026-01-01", "title": "x"} for i in range(10)],
    ]
    top, stats = _call_merge(mod, hf=papers, history=history, days=3, max_age=10)
    assert len(top) == 1, "multi-day mode should not dedup from history"


def test_min_score_filter():
    """Papers below MIN_SCORE are filtered out."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=1)).isoformat()
    papers = [
        make_paper("2605.00008", recent, score=5),
        make_paper("2605.00009", recent, score=0),
    ]
    top, stats = _call_merge(mod, hf=papers, min_score=3)
    assert len(top) == 1
    assert top[0]["score"] == 5


def test_backfill_from_history():
    """When candidates < 20 and some were removed, backfill from history."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=1)).isoformat()
    new_papers = [make_paper(f"2605.1{i:04d}", recent, score=5) for i in range(5)]
    old_papers = [make_paper(f"2605.2{i:04d}", recent, score=4) for i in range(5)]
    all_papers = new_papers + old_papers
    history = [
        *[{"id": f"2605.2{i:04d}", "date": "2026-05-18", "title": "x"} for i in range(5)],
        *[{"id": f"2600.{i:05d}", "date": "2026-01-01", "title": "x"} for i in range(10)],
    ]
    top, stats = _call_merge(mod, hf=all_papers, history=history, min_score=3)
    assert stats["filter_steps"]["history_backfilled"] > 0
    backfilled = [p for p in top if p.get("is_re_recommend")]
    assert len(backfilled) > 0, "should have backfilled papers"


def test_top_n_cap():
    """Output never exceeds top_n."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=1)).isoformat()
    papers = [make_paper(f"2605.3{i:04d}", recent, score=5) for i in range(20)]
    top, stats = _call_merge(mod, hf=papers, top_n=5)
    assert len(top) <= 5, f"expected <= 5, got {len(top)}"


def test_fallback_ids_used_when_history_sparse():
    """When history has < 10 entries, load_fallback_ids scans daily .md files."""
    mod = _import_fetch()
    recent = (TODAY - timedelta(days=1)).isoformat()
    # 21+ new papers to prevent backfill from re-adding the deduped one
    papers = [make_paper(f"2605.5{i:04d}", recent, score=5) for i in range(21)]
    papers.append(make_paper("2605.00050", recent, score=5))

    # Sparse history (< 10 entries, triggers fallback)
    history = [{"id": "2605.99999", "date": "2026-05-01", "title": "x"}]

    # Create a temp dailypapers dir with a fake recommendation .md mentioning 2605.00050
    tmp_dp = Path(tempfile.mkdtemp())
    yesterday = (TODAY - timedelta(days=1)).isoformat()
    md_file = tmp_dp / f"{yesterday}-论文推荐.md"
    md_file.write_text("### 1. Paper\nhttps://arxiv.org/abs/2605.00050\n")

    top, stats = _call_merge(mod, hf=papers, history=history, dailypapers_dir=tmp_dp)
    ids = [p["url"].split("/")[-1] for p in top]
    assert "2605.00050" not in ids, "fallback ID should be deduped"
    assert "2605.00051" not in ids or "2605.50000" in ids  # new papers present


# ── Runner ────────────────────────────────────────────────────────────────

TESTS = [
    test_age_filter_drops_old,
    test_age_filter_keeps_recent,
    test_age_filter_no_date_passes,
    test_merge_keeps_higher_score,
    test_history_dedup_removes_seen,
    test_history_dedup_skipped_multiday,
    test_min_score_filter,
    test_backfill_from_history,
    test_top_n_cap,
    test_fallback_ids_used_when_history_sparse,
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
