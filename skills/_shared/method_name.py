"""Shared method/model name normalization for fuzzy matching.

Handles: subscript digits, Greek letters, &→and, punctuation stripping.
Used by: paper_daemon.py, backfill_links.py

Examples:
    normalize("π0.5")       → "pi05"
    normalize("F5-TTS")     → "f5tts"
    normalize("CosyVoice 2") → "cosyvoice2"
    normalize("GPT-4 & Beyond") → "gpt4andbeyond"
"""

import re

_SUBSCRIPT_TRANSLATION = str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋", "0123456789+-")
_GREEK_REPLACEMENTS = {
    "π": "pi",
    "ϕ": "phi",
    "φ": "phi",
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
}


def normalize(value: str) -> str:
    """Normalize a method/model name for fuzzy matching.

    Lowercases, translates subscript digits, expands Greek, replaces & with and,
    then strips all non-alphanumeric characters.
    """
    result = value.strip().lower().translate(_SUBSCRIPT_TRANSLATION)
    for source, target in _GREEK_REPLACEMENTS.items():
        result = result.replace(source, target)
    result = result.replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", result)
