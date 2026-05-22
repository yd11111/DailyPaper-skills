#!/usr/bin/env python3
"""Tests for library-import/build_manifest.py (P1-6).

Covers: extract_first_page, find_arxiv_id, main() CLI (JSON shape,
topic extraction, missing dir, nested subdirs).

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_build_manifest.py
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST_PY = REPO / "skills" / "library-import" / "build_manifest.py"
SAMPLE_PDF = REPO / "scripts" / "fixtures" / "sample.pdf"


def _import_manifest():
    spec = importlib.util.spec_from_file_location("build_manifest", MANIFEST_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.argv = ["build_manifest.py", "/tmp"]  # prevent argparse crash on import
    spec.loader.exec_module(mod)
    return mod


def _run_cli(*args) -> tuple[int, str, str]:
    cmd = [sys.executable, str(MANIFEST_PY)] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


# ── extract_first_page ────────────────────────────────────────────────────


def test_extract_first_page_real_pdf():
    """extract_first_page returns non-empty text for a valid PDF."""
    mod = _import_manifest()
    text = mod.extract_first_page(SAMPLE_PDF)
    assert len(text) > 0, "expected non-empty text from sample.pdf"


def test_extract_first_page_missing_pdf():
    """extract_first_page returns empty string for a missing file."""
    mod = _import_manifest()
    text = mod.extract_first_page(Path("/tmp/__nonexistent_test_pdf_12345__.pdf"))
    assert text == ""


# ── find_arxiv_id ─────────────────────────────────────────────────────────


def test_find_arxiv_id_present():
    """Finds arxiv ID from typical PDF first-page text."""
    mod = _import_manifest()
    text = "arXiv:2605.12345v2 [cs.SD] 20 May 2026\nTitle of the Paper"
    assert mod.find_arxiv_id(text) == "2605.12345"


def test_find_arxiv_id_in_url():
    """Finds arxiv ID embedded in URL."""
    mod = _import_manifest()
    text = "Published at https://arxiv.org/abs/2401.09876 as a preprint."
    assert mod.find_arxiv_id(text) == "2401.09876"


def test_find_arxiv_id_absent():
    """Returns None when no arxiv ID is present."""
    mod = _import_manifest()
    text = "This is a paper about speech synthesis published in ICASSP 2025."
    assert mod.find_arxiv_id(text) is None


def test_find_arxiv_id_empty():
    mod = _import_manifest()
    assert mod.find_arxiv_id("") is None


# ── main() CLI: JSON shape ────────────────────────────────────────────────


def test_cli_json_shape():
    """CLI produces valid JSON with expected fields for each entry."""
    tmp = Path(tempfile.mkdtemp())
    out = tmp / "manifest.json"
    # Create a library with one PDF
    topic_dir = tmp / "TTS"
    topic_dir.mkdir()
    shutil.copy(SAMPLE_PDF, topic_dir / "paper1.pdf")

    code, stdout, stderr = _run_cli(str(tmp), "--out", str(out))
    assert code == 0, f"exit {code}: {stderr}"
    assert out.exists(), "output JSON not created"

    entries = json.loads(out.read_text())
    assert len(entries) == 1

    e = entries[0]
    required_keys = {
        "filename", "absolute_path", "relative_path", "source_topic",
        "first_page_text", "first_page_chars", "arxiv_id", "file_size_bytes",
    }
    assert required_keys.issubset(set(e.keys())), f"missing keys: {required_keys - set(e.keys())}"
    assert e["filename"] == "paper1.pdf"
    assert e["source_topic"] == "TTS"
    assert e["file_size_bytes"] > 0


def test_cli_topic_from_subdir():
    """source_topic comes from the first-level subdirectory name."""
    tmp = Path(tempfile.mkdtemp())
    out = tmp / "manifest.json"
    # Nested: AudioCodec/sub/paper.pdf → topic = "AudioCodec"
    nested = tmp / "AudioCodec" / "sub"
    nested.mkdir(parents=True)
    shutil.copy(SAMPLE_PDF, nested / "deep.pdf")

    code, _, _ = _run_cli(str(tmp), "--out", str(out))
    assert code == 0

    entries = json.loads(out.read_text())
    assert entries[0]["source_topic"] == "AudioCodec"


def test_cli_root_topic():
    """PDFs directly in root get source_topic = '_root'."""
    tmp = Path(tempfile.mkdtemp())
    out = tmp / "manifest.json"
    shutil.copy(SAMPLE_PDF, tmp / "loose.pdf")

    code, _, _ = _run_cli(str(tmp), "--out", str(out))
    assert code == 0

    entries = json.loads(out.read_text())
    assert entries[0]["source_topic"] == "_root"


def test_cli_missing_dir():
    """CLI exits with code 2 when given a nonexistent directory."""
    code, _, stderr = _run_cli("/tmp/__nonexistent_library_dir_xyz__")
    assert code == 2


def test_cli_empty_dir():
    """CLI handles an empty directory gracefully (0 entries)."""
    tmp = Path(tempfile.mkdtemp())
    out = tmp / "manifest.json"
    code, _, _ = _run_cli(str(tmp), "--out", str(out))
    assert code == 0
    entries = json.loads(out.read_text())
    assert entries == []


# ── Runner ────────────────────────────────────────────────────────────────

TESTS = [
    test_extract_first_page_real_pdf,
    test_extract_first_page_missing_pdf,
    test_find_arxiv_id_present,
    test_find_arxiv_id_in_url,
    test_find_arxiv_id_absent,
    test_find_arxiv_id_empty,
    test_cli_json_shape,
    test_cli_topic_from_subdir,
    test_cli_root_topic,
    test_cli_missing_dir,
    test_cli_empty_dir,
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
