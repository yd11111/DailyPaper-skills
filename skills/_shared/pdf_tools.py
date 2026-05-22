#!/usr/bin/env python3
"""pdf_tools.py — spec #2: centralized PDF text + image extraction.

Stdlib only. Wraps `pdftotext` + `pdfimages` (poppler-utils).
URL inputs are pipe-fetched via `curl`.

Callers: build_manifest.py, enrich_papers.py, download_note_images.py.

Error model:
  - Missing binary (pdftotext / pdfimages / curl)  → RuntimeError
  - PDF parse failure / network failure / timeout  → "" or []
  - extract_images called on missing PDF           → FileNotFoundError
  - extract_text called on missing local PDF       → "" (pdftotext fails internally)
"""

import shutil
import subprocess
from pathlib import Path

from user_config import timeouts_config as _timeouts_config

_PDF_TIMEOUT = _timeouts_config().get("pdf_extract", 30)


def _check_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(
            f"{name} not found on PATH. Install poppler-utils: "
            f"macOS `brew install poppler` / "
            f"Debian/Ubuntu `apt install poppler-utils` / "
            f"Windows `choco install poppler`"
        )


def _is_url(s: object) -> bool:
    return isinstance(s, str) and s.startswith(("http://", "https://"))


def _pdftotext_page_args(first_n_pages: int | None) -> list[str]:
    return ["-l", str(first_n_pages)] if first_n_pages else []


def _extract_text_local(path: Path, first_n_pages: int | None, timeout: int) -> str:
    args = ["pdftotext"] + _pdftotext_page_args(first_n_pages) + [str(path), "-"]
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _extract_text_url(url: str, first_n_pages: int | None, timeout: int) -> str:
    # Two subprocesses + stdin pipe (no shell=True) so untrusted URLs cannot
    # inject shell metacharacters. curl's --max-time caps the network side;
    # the outer subprocess timeout is a safety net (+2s) for curl exit.
    # pdftotext gets `timeout=timeout` (parsing in-memory bytes is fast).
    # Worst-case wall time = (timeout + 2) + timeout = 2*timeout + 2.
    try:
        curl_proc = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), url],
            capture_output=True, timeout=timeout + 2,
        )
        if curl_proc.returncode != 0 or not curl_proc.stdout:
            return ""
        pdf_args = ["pdftotext"] + _pdftotext_page_args(first_n_pages) + ["-", "-"]
        pdf_proc = subprocess.run(
            pdf_args, input=curl_proc.stdout, capture_output=True, timeout=timeout,
        )
        if pdf_proc.returncode != 0:
            return ""
        return pdf_proc.stdout.decode("utf-8", errors="replace")
    except (subprocess.TimeoutExpired, OSError):
        return ""


def extract_text(
    source,
    first_n_pages: int | None = None,
    timeout: int = 30,
) -> str:
    """Extract plain text from a PDF.

    `source`:
      - URL string ('http://...' or 'https://...') → curl pipe
      - Path or str path                          → local pdftotext

    `first_n_pages`: if set, only pages 1..N (pdftotext -l N)
    `timeout`: per-subprocess timeout in seconds (default 30)

    Returns: extracted text, or "" on PDF parse / network failure.
    Raises:  RuntimeError if pdftotext (or curl, for URL inputs) is not installed.
    """
    _check_binary("pdftotext")
    if _is_url(source):
        _check_binary("curl")
        return _extract_text_url(source, first_n_pages, timeout)
    return _extract_text_local(Path(source), first_n_pages, timeout)


def extract_images(
    pdf_path,
    out_dir,
    prefix: str,
    min_size_bytes: int = 10240,
) -> list[Path]:
    """Extract images from a local PDF using pdfimages.

    Writes `<out_dir>/<prefix>-NNN.png` files. Returns list of Path
    objects sorted by name, filtered to >= min_size_bytes
    (default 10 KB — drops tiny icons/decorations).

    Returns: list of Path (possibly empty).
    Raises:  RuntimeError if pdfimages not installed.
             FileNotFoundError if pdf_path missing.
    """
    _check_binary("pdfimages")
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(str(pdf))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["pdfimages", "-png", str(pdf), str(out / prefix)],
            check=True, capture_output=True, timeout=_PDF_TIMEOUT,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return []
    return sorted(
        p for p in out.glob(f"{prefix}-*.png")
        if p.stat().st_size >= min_size_bytes
    )
