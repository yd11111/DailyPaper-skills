"""Shared history store for daily-papers recommendation dedup.

Single source of truth for .history.json path, load, save, append, prune.
Used by: fetch_and_score.py (read), update_history.py (read+write).
"""

import json
from datetime import datetime, timedelta

from user_config import daily_papers_dir

HISTORY_PATH = daily_papers_dir() / ".history.json"
DAYS_TO_KEEP = 30


def load() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return []


def save(history: list[dict]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def append(entries: list[dict], date: str, preserve_earliest: bool = True) -> int:
    """Add new entries to history, return count of newly added."""
    history = load()
    existing_ids = {h.get("id") for h in history if h.get("id")}
    added = 0

    for entry in entries:
        aid = entry.get("id", "")
        if not aid:
            continue
        if aid not in existing_ids:
            history.append({"id": aid, "date": date, "title": entry.get("title", "")})
            existing_ids.add(aid)
            added += 1
        elif preserve_earliest:
            for h in history:
                if h.get("id") == aid:
                    if h.get("date", "") > date:
                        h["date"] = date
                    break

    save(history)
    return added


def prune(reference_date: str | None = None, days: int = DAYS_TO_KEEP) -> int:
    """Remove entries older than `days` from reference_date. Returns removed count."""
    ref = datetime.strptime(reference_date, "%Y-%m-%d") if reference_date else datetime.now()
    cutoff = (ref - timedelta(days=days)).strftime("%Y-%m-%d")
    history = load()
    before = len(history)
    history = [h for h in history if h.get("date", "") >= cutoff]
    save(history)
    return before - len(history)
