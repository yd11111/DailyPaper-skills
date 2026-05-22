#!/usr/bin/env python3
"""Tests for skills/_shared/scholarly_api.py

Run:
    python3 -m pytest scripts/test_scholarly_api.py -v
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SHARED_DIR = Path(__file__).resolve().parents[1] / "skills" / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

import scholarly_api


# ── Fixtures ──────────────────────────────────────────────────────────────────

S2_RESPONSE = {
    "externalIds": {"ArXiv": "2406.12345", "DOI": "10.1234/example.2024"},
    "citationCount": 42,
    "influentialCitationCount": 5,
    "venue": "ICASSP 2026",
    "year": 2026,
    "authors": [
        {"authorId": "1", "name": "Alice", "affiliations": ["MIT"]},
        {"authorId": "2", "name": "Bob", "affiliations": ["Google", "Stanford"]},
        {"authorId": "3", "name": "Charlie", "affiliations": None},
    ],
    "tldr": {"model": "tldr@v2", "text": "This paper proposes a novel TTS system."},
}

S2_RESPONSE_MINIMAL = {
    "externalIds": {},
    "citationCount": 0,
    "influentialCitationCount": 0,
    "venue": "",
    "year": 2026,
    "authors": [],
    "tldr": None,
}

OPENALEX_RESPONSE = {
    "id": "https://openalex.org/W123456",
    "doi": "https://doi.org/10.1234/example.2024",
    "cited_by_count": 18,
    "authorships": [
        {
            "author": {"display_name": "Alice"},
            "institutions": [
                {"display_name": "MIT", "ror": "https://ror.org/042nb2s44"},
            ],
        },
        {
            "author": {"display_name": "Bob"},
            "institutions": [
                {"display_name": "Google DeepMind", "ror": None},
            ],
        },
    ],
    "primary_location": {
        "source": {"display_name": "IEEE Signal Processing Letters"},
    },
}


# ── _parse_s2_response tests ─────────────────────────────────────────────────

def test_parse_s2_full():
    result = scholarly_api._parse_s2_response(S2_RESPONSE)
    assert result["doi"] == "10.1234/example.2024"
    assert result["citation_count"] == 42
    assert result["influential_citation_count"] == 5
    assert result["venue"] == "ICASSP 2026"
    assert result["s2_affiliations"] == ["MIT", "Google", "Stanford"]
    assert result["tldr"] == "This paper proposes a novel TTS system."


def test_parse_s2_minimal():
    result = scholarly_api._parse_s2_response(S2_RESPONSE_MINIMAL)
    assert result["doi"] == ""
    assert result["citation_count"] == 0
    assert result["s2_affiliations"] == []
    assert result["tldr"] == ""


def test_parse_s2_deduplicates_affiliations():
    data = {
        **S2_RESPONSE,
        "authors": [
            {"authorId": "1", "name": "A", "affiliations": ["MIT"]},
            {"authorId": "2", "name": "B", "affiliations": ["MIT", "Google"]},
        ],
    }
    result = scholarly_api._parse_s2_response(data)
    assert result["s2_affiliations"] == ["MIT", "Google"]


def test_parse_s2_null_fields():
    data = {
        "externalIds": None,
        "citationCount": None,
        "influentialCitationCount": None,
        "venue": None,
        "authors": None,
        "tldr": None,
    }
    result = scholarly_api._parse_s2_response(data)
    assert result["doi"] == ""
    assert result["citation_count"] == 0
    assert result["s2_affiliations"] == []


# ── _parse_openalex_response tests ───────────────────────────────────────────

def test_parse_openalex_full():
    result = scholarly_api._parse_openalex_response(OPENALEX_RESPONSE)
    assert result["doi"] == "10.1234/example.2024"
    assert result["citation_count"] == 18
    assert result["influential_citation_count"] == 0
    assert result["venue"] == "IEEE Signal Processing Letters"
    assert result["s2_affiliations"] == ["MIT", "Google DeepMind"]
    assert result["tldr"] == ""


def test_parse_openalex_empty():
    result = scholarly_api._parse_openalex_response({})
    assert result["doi"] == ""
    assert result["citation_count"] == 0
    assert result["venue"] == ""
    assert result["s2_affiliations"] == []


def test_parse_openalex_no_location():
    data = {**OPENALEX_RESPONSE, "primary_location": None}
    result = scholarly_api._parse_openalex_response(data)
    assert result["venue"] == ""


# ── fetch_scholarly integration tests (mocked HTTP) ──────────────────────────

def _make_mock_fetch(responses: dict):
    """Create a mock _sync_fetch that returns based on URL patterns."""
    def mock_fetch(url, headers=None, timeout=15):
        if "semanticscholar" in url:
            if "s2_error" in responses:
                raise responses["s2_error"]
            return json.dumps(responses.get("s2", {}))
        elif "openalex" in url:
            if "oa_error" in responses:
                raise responses["oa_error"]
            # OpenAlex returns results wrapped in {"results": [...]}
            oa_data = responses.get("oa", {})
            return json.dumps({"results": [oa_data]} if oa_data else {"results": []})
        return ""
    return mock_fetch


def test_fetch_scholarly_s2_success():
    mock = _make_mock_fetch({"s2": S2_RESPONSE})
    with patch.object(scholarly_api, "_sync_fetch", side_effect=mock):
        result = asyncio.run(scholarly_api.fetch_scholarly("2406.12345"))
    assert result["doi"] == "10.1234/example.2024"
    assert result["citation_count"] == 42


def test_fetch_scholarly_s2_fails_openalex_fallback():
    mock = _make_mock_fetch({
        "s2_error": OSError("API error: rate limited"),
        "oa": OPENALEX_RESPONSE,
    })
    with patch.object(scholarly_api, "_sync_fetch", side_effect=mock):
        result = asyncio.run(scholarly_api.fetch_scholarly("2406.12345"))
    assert result["doi"] == "10.1234/example.2024"
    assert result["citation_count"] == 18
    assert result["venue"] == "IEEE Signal Processing Letters"


def test_fetch_scholarly_both_fail():
    mock = _make_mock_fetch({
        "s2_error": OSError("API error: server error"),
        "oa_error": OSError("API error: not found"),
    })
    with patch.object(scholarly_api, "_sync_fetch", side_effect=mock):
        result = asyncio.run(scholarly_api.fetch_scholarly("2406.99999"))
    assert result["doi"] == ""
    assert result["citation_count"] == 0


def test_fetch_scholarly_disabled():
    with patch.object(scholarly_api, "scholarly_api_config", return_value={"enabled": False}):
        result = asyncio.run(scholarly_api.fetch_scholarly("2406.12345"))
    assert result == scholarly_api._empty_result()


def test_fetch_scholarly_s2_zero_citations_still_returns():
    """S2 returns 0 citations but has DOI — should still use S2 result."""
    data = {**S2_RESPONSE, "citationCount": 0}
    mock = _make_mock_fetch({"s2": data})
    with patch.object(scholarly_api, "_sync_fetch", side_effect=mock):
        result = asyncio.run(scholarly_api.fetch_scholarly("2406.12345"))
    # S2 returned 0 citations → triggers OpenAlex check
    # But since OpenAlex also not mocked to succeed, falls back to S2 partial
    assert result["doi"] == "10.1234/example.2024"


def test_empty_result():
    r = scholarly_api._empty_result()
    assert r["doi"] == ""
    assert r["citation_count"] == 0
    assert r["influential_citation_count"] == 0
    assert r["venue"] == ""
    assert r["s2_affiliations"] == []
    assert r["tldr"] == ""
