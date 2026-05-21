#!/usr/bin/env python3
"""Tests for skills/_shared/pdf_tools.py (spec #2).

Stdlib only. Tests local-path branches; URL branch validated only
in caller migration smoke (per spec §6).

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_pdf_tools.py
"""

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path("/Users/xiangshu/DailyPaper")
MODULE = REPO / "skills" / "_shared" / "pdf_tools.py"
FIXTURE = REPO / "scripts" / "fixtures" / "sample.pdf"

# Put skills/_shared on sys.path so `import pdf_tools` and
# `importlib.reload(pdf_tools)` both work via the standard PathFinder.
_SHARED_DIR = str(MODULE.parent)
if _SHARED_DIR not in sys.path:
    sys.path.insert(0, _SHARED_DIR)


def _import_module():
    # Use the standard import machinery (PathFinder) so importlib.reload
    # in test_binary_missing_raises can find the spec.
    if "pdf_tools" in sys.modules:
        del sys.modules["pdf_tools"]
    import importlib
    return importlib.import_module("pdf_tools")


def test_extract_text_local():
    """sample.pdf → text contains 'Sample PDF'."""
    mod = _import_module()
    text = mod.extract_text(FIXTURE)
    assert isinstance(text, str), f"expected str, got {type(text)}"
    assert "Sample PDF" in text, f"'Sample PDF' not in extracted text: {text[:200]!r}"


def test_extract_text_first_n_pages():
    """first_n_pages=1 must exclude 'Page Two Only'."""
    mod = _import_module()
    text = mod.extract_text(FIXTURE, first_n_pages=1)
    assert "Sample PDF" in text, "page 1 missing"
    assert "Page Two Only" not in text, (
        f"first_n_pages=1 still leaked page 2 content: {text[-200:]!r}"
    )


def test_extract_text_missing_file():
    """Non-existent PDF → return ''."""
    mod = _import_module()
    text = mod.extract_text("/tmp/__not_a_real_pdf_for_pdf_tools_test__.pdf")
    assert text == "", f"expected empty string, got {text!r}"


def test_extract_images():
    """sample.pdf → at least 1 image >= 10 240 bytes returned."""
    mod = _import_module()
    with tempfile.TemporaryDirectory() as td:
        results = mod.extract_images(FIXTURE, td, "test_img", min_size_bytes=10240)
    assert isinstance(results, list), f"expected list, got {type(results)}"
    assert len(results) >= 1, f"no images >= 10 KB extracted; got {results}"
    for p in results:
        assert isinstance(p, Path), f"item not Path: {p!r}"


def test_extract_images_pdf_missing():
    """Non-existent PDF → raise FileNotFoundError."""
    mod = _import_module()
    raised = False
    try:
        with tempfile.TemporaryDirectory() as td:
            mod.extract_images("/tmp/__nope__.pdf", td, "x")
    except FileNotFoundError:
        raised = True
    assert raised, "expected FileNotFoundError, got nothing"


def test_binary_missing_raises():
    """Monkey-patch shutil.which to simulate pdftotext missing → RuntimeError."""
    mod = _import_module()
    orig_which = shutil.which
    try:
        # Patch the which used inside pdf_tools (it imports shutil and calls
        # shutil.which inside _check_binary).
        shutil.which = lambda name: None
        # Re-import the module so _check_binary picks up the patched which.
        # Easier: monkey-patch the module's own attribute if it does
        # `from shutil import which` — but the spec uses `shutil.which()`.
        # Force a reload to be safe:
        import importlib
        importlib.reload(mod)
        raised = False
        try:
            mod.extract_text(FIXTURE)
        except RuntimeError as e:
            raised = "pdftotext" in str(e) or "not installed" in str(e)
        assert raised, "expected RuntimeError mentioning pdftotext"
    finally:
        shutil.which = orig_which
        importlib.reload(mod)


TESTS = [
    test_extract_text_local,
    test_extract_text_first_n_pages,
    test_extract_text_missing_file,
    test_extract_images,
    test_extract_images_pdf_missing,
    test_binary_missing_raises,
]


def main():
    if not MODULE.exists():
        print(f"NOTE: {MODULE} does not exist — all tests will fail/error by design (TDD red phase).")
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
