#!/usr/bin/env python3
"""
update_history.py - Update the recommendation history file.

This script is part of daily-papers-review (Phase 6).

Usage:
    python3 update_history.py --arxiv-ids ID1 ID2 ... --date YYYY-MM-DD
    python3 update_history.py --from-enriched /tmp/daily_papers_enriched.json --date YYYY-MM-DD
    python3 update_history.py --from-recommendation YYYY-MM-DD-论文推荐.md --date YYYY-MM-DD

    # Cross-platform (auto-detect paths)
    python3 update_history.py --date 2026-03-17

The script:
1. Reads existing history from {vault}/DailyPapers/.history.json
2. Adds new entries for papers not already in history
3. Preserves the earliest date for papers that are re-recommended
4. Removes entries older than 30 days
5. Writes back to .history.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent.parent / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from arxiv_id import extract_id as _extract_arxiv_id, extract_all_ids
from user_config import temp_file_path
import history_store as _history_store




def load_from_enriched(path: str) -> list:
    """Load papers from enriched JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        papers = json.load(f)

    entries = []
    for p in papers:
        arxiv_id = p.get('arxiv_id', '')
        if not arxiv_id:
            url = p.get('url', '')
            arxiv_id = _extract_arxiv_id(url)

        if arxiv_id:
            entries.append({
                'id': arxiv_id,
                'title': p.get('title', '')[:200],
                'score': p.get('score', 0),
            })
    return entries


def load_from_recommendation(path: str) -> list:
    """Load papers from recommendation markdown file."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    arxiv_ids = extract_all_ids(content)

    # Extract paper titles (### N. Title pattern)
    titles = {}
    for m in re.finditer(r'^### \d+\. (.+)$', content, re.MULTILINE):
        title = m.group(1).strip()
        # Extract arXiv ID from nearby lines
        idx = len(titles)
        titles[idx] = title

    entries = []
    for arxiv_id in arxiv_ids:
        entries.append({
            'id': arxiv_id,
            'title': '',  # Would need more complex parsing to match
        })
    return entries


def update_history(entries: list, date: str, preserve_earliest: bool = True):
    """Update history with new entries."""
    added = _history_store.append(entries, date, preserve_earliest=preserve_earliest)
    _history_store.prune(reference_date=date)
    return added


def main():
    parser = argparse.ArgumentParser(description='Update recommendation history')
    parser.add_argument('--arxiv-ids', nargs='+', help='arXiv IDs to add')
    parser.add_argument('--from-enriched', help='Path to enriched JSON file')
    parser.add_argument('--from-recommendation', help='Path to recommendation markdown file')
    parser.add_argument('--date', required=True, help='Date (YYYY-MM-DD)')

    args = parser.parse_args()

    entries = []

    if args.arxiv_ids:
        entries = [{'id': aid, 'title': ''} for aid in args.arxiv_ids]
    elif args.from_enriched:
        entries = load_from_enriched(args.from_enriched)
    elif args.from_recommendation:
        entries = load_from_recommendation(args.from_recommendation)
    else:
        # Auto-detect: try to load from default temp path
        auto_enriched = temp_file_path('daily_papers_enriched.json')
        if auto_enriched.exists():
            print(f"[update_history] Auto-detected input: {auto_enriched}", file=sys.stderr)
            entries = load_from_enriched(str(auto_enriched))
        else:
            print("Error: Must specify --arxiv-ids, --from-enriched, or --from-recommendation", file=sys.stderr)
            print(f"  Or ensure {temp_file_path('daily_papers_enriched.json')} exists", file=sys.stderr)
            sys.exit(1)

    added = update_history(entries, args.date)
    print(f"Added {added} new entries to history")


if __name__ == '__main__':
    main()
