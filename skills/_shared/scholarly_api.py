#!/usr/bin/env python3
"""Fetch citation/DOI/venue metadata from Semantic Scholar and OpenAlex.

Used by enrich_papers.py as a fourth enrichment layer after HTML/abs/PDF.
Rate-limited: S2 free tier = 1 req/s (Semaphore(1) + sleep).
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from user_config import scholarly_api_config

_S2_FIELDS = ",".join([
    "externalIds",
    "citationCount",
    "influentialCitationCount",
    "venue",
    "year",
    "authors.affiliations",
    "tldr",
])

_config = scholarly_api_config()
_S2_KEY = _config.get("semantic_scholar_key", "")
_OA_EMAIL = _config.get("openalex_email", "")

_s2_sem: asyncio.Semaphore | None = None


def _get_s2_sem() -> asyncio.Semaphore:
    global _s2_sem
    if _s2_sem is None:
        limit = 8 if _S2_KEY else 1
        _s2_sem = asyncio.Semaphore(limit)
    return _s2_sem


def _sync_fetch(url: str, headers: dict | None = None, timeout: int = 15) -> str:
    """Fetch URL via subprocess curl (avoids Python SSL cert issues)."""
    cmd = ["curl", "-s", "--max-time", str(timeout), "-H", "Accept: application/json"]
    for key, val in (headers or {}).items():
        cmd += ["-H", f"{key}: {val}"]
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise OSError(f"curl failed (rc={proc.returncode}): {proc.stderr[:100]}")
    if not proc.stdout.strip():
        raise OSError(f"curl returned empty response for {url}")
    # Detect HTTP errors in JSON response (S2 returns {"error": ..., "message": ...})
    if proc.stdout.strip().startswith("{"):
        try:
            data = json.loads(proc.stdout)
            if "error" in data and "message" in data:
                raise OSError(f"API error: {data['message']}")
        except json.JSONDecodeError:
            pass
    return proc.stdout


def _parse_s2_response(data: dict) -> dict:
    ext_ids = data.get("externalIds") or {}
    doi = ext_ids.get("DOI", "")

    authors = data.get("authors") or []
    affiliations = []
    for author in authors:
        for aff in (author.get("affiliations") or []):
            if aff and aff not in affiliations:
                affiliations.append(aff)

    tldr_obj = data.get("tldr")
    tldr = tldr_obj.get("text", "") if isinstance(tldr_obj, dict) else ""

    return {
        "doi": doi,
        "citation_count": data.get("citationCount") or 0,
        "influential_citation_count": data.get("influentialCitationCount") or 0,
        "venue": data.get("venue") or "",
        "s2_affiliations": affiliations,
        "tldr": tldr,
    }


def _parse_openalex_response(data: dict) -> dict:
    doi_raw = data.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "") if doi_raw else ""

    affiliations = []
    for authorship in (data.get("authorships") or []):
        for inst in (authorship.get("institutions") or []):
            name = inst.get("display_name", "")
            if name and name not in affiliations:
                affiliations.append(name)

    loc = data.get("primary_location") or {}
    source = loc.get("source") or {}
    venue = source.get("display_name") or ""

    return {
        "doi": doi,
        "citation_count": data.get("cited_by_count") or 0,
        "influential_citation_count": 0,
        "venue": venue,
        "s2_affiliations": affiliations,
        "tldr": "",
    }


async def fetch_semantic_scholar(arxiv_id: str) -> dict | None:
    """Query S2 Graph API by arXiv ID. Returns parsed dict or None on failure."""
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}?fields={_S2_FIELDS}"
    headers = {}
    if _S2_KEY:
        headers["x-api-key"] = _S2_KEY

    sem = _get_s2_sem()
    async with sem:
        try:
            raw = await asyncio.get_event_loop().run_in_executor(
                None, lambda: _sync_fetch(url, headers)
            )
            if not _S2_KEY:
                await asyncio.sleep(1.1)
            data = json.loads(raw)
            return _parse_s2_response(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [s2] {arxiv_id}: {e}", file=sys.stderr)
            return None


async def fetch_openalex(arxiv_id: str) -> dict | None:
    """Fallback: query OpenAlex by arXiv DOI (10.48550/arXiv.{id})."""
    arxiv_doi = f"10.48550/arXiv.{arxiv_id}"
    base = "https://api.openalex.org/works"
    url = f"{base}?filter=doi:{arxiv_doi}&per_page=1"
    if _OA_EMAIL:
        url += f"&mailto={_OA_EMAIL}"

    try:
        raw = await asyncio.get_event_loop().run_in_executor(
            None, lambda: _sync_fetch(url, timeout=10)
        )
        data = json.loads(raw)
        results = data.get("results", [])
        if not results:
            return None
        return _parse_openalex_response(results[0])
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [openalex] {arxiv_id}: {e}", file=sys.stderr)
        return None


async def fetch_scholarly(arxiv_id: str) -> dict:
    """Unified entry: try S2 first, fallback to OpenAlex. Always returns a dict."""
    if not scholarly_api_config().get("enabled", True):
        return _empty_result()

    result = await fetch_semantic_scholar(arxiv_id)
    if result and result.get("citation_count", 0) > 0:
        return result

    # S2 returned nothing useful — try OpenAlex
    if result is None:
        oa_result = await fetch_openalex(arxiv_id)
        if oa_result:
            return oa_result

    # S2 returned partial data (0 citations but has DOI/venue) — still usable
    if result:
        return result

    return _empty_result()


def _empty_result() -> dict:
    return {
        "doi": "",
        "citation_count": 0,
        "influential_citation_count": 0,
        "venue": "",
        "s2_affiliations": [],
        "tldr": "",
    }
