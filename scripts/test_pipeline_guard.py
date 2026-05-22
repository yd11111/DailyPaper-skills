#!/usr/bin/env python3
"""Tests for pipeline_guard.py (spec #3).

Runs each test as a subprocess against the real CLI, exactly as
daily-papers-review will invoke it. Stdlib only — no pytest.

Run:
    python3 scripts/test_pipeline_guard.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "skills" / "_shared" / "pipeline_guard.py"
FIX = REPO / "scripts" / "fixtures"
ENRICHED = FIX / "enriched.json"
META = FIX / "meta.json"
NOTES = FIX / "notes"


def run_guard(draft_name: str, json_out: Path,
              enriched: Path = ENRICHED, meta: Path = META,
              notes: Path = NOTES) -> tuple[int, dict | None]:
    """Run guard and return (exit_code, parsed_report_or_None)."""
    cmd = [
        sys.executable, str(GUARD),
        str(FIX / draft_name),
        "--enriched", str(enriched),
        "--meta", str(meta),
        "--notes", str(notes),
        "--json-out", str(json_out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    report = None
    if json_out.exists():
        try:
            report = json.loads(json_out.read_text())
        except json.JSONDecodeError:
            pass
    return proc.returncode, report


def _tmp_json() -> Path:
    fd, path = tempfile.mkstemp(suffix=".json", prefix="guard_test_")
    import os; os.close(fd)
    return Path(path)


def test_passing_draft():
    """All 3 checks pass — exit 0, no violations."""
    code, report = run_guard("draft_passing.md", _tmp_json())
    assert code == 0, f"expected exit 0, got {code}"
    assert report is not None, "no report written"
    assert report["passed"] is True
    assert report["summary"]["total_violations"] == 0


def test_date_cutoff_violation():
    """1 paper with date < cutoff → C1 violation."""
    code, report = run_guard("draft_date_violation.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    assert report["passed"] is False
    assert report["summary"]["by_check"]["date_cutoff"] >= 1
    dc = [v for v in report["violations"] if v["check"] == "date_cutoff"]
    assert dc, "no date_cutoff violation in report"
    assert dc[0]["paper_arxiv_id"] == "2508.19205"
    assert dc[0]["paper_published_date"] == "2025-08-15"
    assert dc[0]["age_cutoff"] == "2026-05-13"


def test_existing_note_wikilink_missing():
    """`📒 **已有笔记**: [[FakeNote]]` → C2 violation."""
    code, report = run_guard("draft_wikilink_missing.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    assert report["summary"]["by_check"]["existing_note_wikilink"] >= 1
    wk = [v for v in report["violations"] if v["check"] == "existing_note_wikilink"]
    assert wk, "no existing_note_wikilink violation in report"
    assert wk[0]["wikilink"] == "FakeNote"


def test_critique_triple_missing():
    """Paper with only 1 Claim/Evidence/Confidence triple → C3 violation."""
    code, report = run_guard("draft_triple_missing.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    assert report["summary"]["by_check"]["critique_evidence_triples"] >= 1
    tr = [v for v in report["violations"] if v["check"] == "critique_evidence_triples"]
    assert tr, "no critique_evidence_triples violation in report"
    assert tr[0]["triple_count"] == 1
    assert tr[0]["minimum_required"] == 2


def test_skip_existing_note_paper_for_c3():
    """Paper marked `📒 **已有笔记**: [[RealNote]]` + missing 🧪 block → C3 should SKIP, C2 should PASS (RealNote.md exists), exit 0."""
    code, report = run_guard("draft_skip_existing_note.md", _tmp_json())
    assert code == 0, f"expected exit 0, got {code}; violations={report.get('violations') if report else 'no report'}"
    assert report["summary"]["total_violations"] == 0
    assert report["summary"]["stats"]["papers_skipped_for_C3"] >= 1


def test_combined_violations():
    """All 3 violation types present → all 3 reported, exit 1."""
    code, report = run_guard("draft_combined.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    bc = report["summary"]["by_check"]
    assert bc["date_cutoff"] >= 1
    assert bc["existing_note_wikilink"] >= 1
    assert bc["critique_evidence_triples"] >= 1


def test_enriched_data_missing():
    """Missing enriched.json → exit 2 (guard error, not violation)."""
    bogus = Path("/tmp/__definitely_not_a_real_file__.json")
    if bogus.exists():
        bogus.unlink()
    code, report = run_guard("draft_passing.md", _tmp_json(), enriched=bogus)
    assert code == 2, f"expected exit 2 (guard error), got {code}"


TESTS = [
    test_passing_draft,
    test_date_cutoff_violation,
    test_existing_note_wikilink_missing,
    test_critique_triple_missing,
    test_skip_existing_note_paper_for_c3,
    test_combined_violations,
    test_enriched_data_missing,
]


def main():
    if not GUARD.exists():
        print(f"NOTE: {GUARD} does not exist — all tests will fail by design (TDD red phase).")
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
