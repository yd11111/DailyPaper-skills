#!/usr/bin/env python3
"""Centralized arXiv ID extraction — single source of truth for the pipeline."""

import re

_ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b")


def extract_id(text: str) -> str:
    """Extract first arXiv ID from text (URL, path, or plain text).

    Strips vN suffix. Returns "" if no match.
    """
    m = _ARXIV_ID_RE.search(text)
    return m.group(1) if m else ""


def extract_all_ids(text: str) -> list[str]:
    """Extract all unique arXiv IDs from text, preserving order. Strips vN suffixes."""
    seen = set()
    result = []
    for m in _ARXIV_ID_RE.finditer(text):
        aid = m.group(1)
        if aid not in seen:
            seen.add(aid)
            result.append(aid)
    return result
