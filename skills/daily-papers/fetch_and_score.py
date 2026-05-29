#!/usr/bin/env python3
"""
fetch_and_score.py — Phase 1+2: Fetch, score, merge, dedup, select top 30.

Replaces the two LLM Task Agents with pure Python. Zero token cost.

Usage:
    python3 fetch_and_score.py > /tmp/daily_papers_top30.json
    python3 fetch_and_score.py --date 2026-02-25 > /tmp/daily_papers_top30.json
    python3 fetch_and_score.py --days 7 > /tmp/daily_papers_top30.json

Stderr: progress logs.  Stdout: JSON array of top papers (30 * days).
"""

import argparse
import json
import os
import re
import socket
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_SHARED_DIR = Path(__file__).resolve().parent.parent / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from arxiv_id import extract_id as extract_arxiv_id, extract_all_ids
from user_config import daily_papers_config, daily_papers_dir, timeouts_config

# ── Configuration ──────────────────────────────────────────────────────────

_CONFIG = daily_papers_config()

KEYWORDS = _CONFIG["keywords"]
NEGATIVE_KEYWORDS = _CONFIG["negative_keywords"]
DOMAIN_BOOST_KEYWORDS = _CONFIG["domain_boost_keywords"]
ARXIV_CATEGORIES = _CONFIG["arxiv_categories"]
TECH_REPORT_INSTITUTIONS = _CONFIG.get("tech_report_boost_institutions", [])
MIN_SCORE = _CONFIG["min_score"]
TOP_N = _CONFIG["top_n"]
# 论文 published date 距今最大允许天数；超龄一律剔除
MAX_AGE_DAYS = _CONFIG.get("max_age_days", 7)

DAILYPAPERS_DIR = daily_papers_dir()
import history_store as _history_store
HISTORY_PATH = _history_store.HISTORY_PATH

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# ── Scoring ────────────────────────────────────────────────────────────────


def score_paper(paper: dict) -> int:
    text = (paper["title"] + " " + paper["abstract"]).lower()
    title_lower = paper["title"].lower()

    # 1. Negative keywords → instant reject
    for neg in NEGATIVE_KEYWORDS:
        if neg in text:
            return -999

    score = 0

    # 2. Positive keywords
    for kw in KEYWORDS:
        if kw in title_lower:
            score += 3
        elif kw in text:
            score += 1

    # 3. Domain boost
    domain_hits = sum(1 for kw in DOMAIN_BOOST_KEYWORDS if kw in text)
    if domain_hits >= 2:
        score += 2
    elif domain_hits == 1:
        score += 1

    # 4. Tech report from known speech/audio institutions: +3
    if TECH_REPORT_INSTITUTIONS and "technical report" in title_lower:
        authors_aff = (paper.get("authors", "") + " " + paper.get("affiliations", "")).lower()
        combined = text + " " + authors_aff
        if any(inst in combined for inst in TECH_REPORT_INSTITUTIONS):
            score += 3

    return score


# ── Fetchers ───────────────────────────────────────────────────────────────


_ARXIV_TIMEOUT = timeouts_config().get("arxiv_fetch", 30)
_RETRY_BACKOFFS = (2, 5, 15)  # seconds between attempts; len() == default retry count


def fetch_url(url: str, timeout: int = _ARXIV_TIMEOUT, retries: int = 0) -> tuple[str, str]:
    """Fetch URL, optionally retrying on transient errors.

    Returns (body, status). status is one of:
      "ok"               — succeeded on first attempt
      "retry_recovered"  — succeeded after one or more retries
      "failed: <reason>" — all attempts failed (body == "")

    Retry triggers (when retries > 0): timeout, connection error, HTTP 429, HTTP 5xx.
    Permanent errors (4xx other than 429) do not retry.
    """
    last_err = ""
    attempts = retries + 1
    for attempt in range(attempts):
        try:
            req = Request(url, headers={"User-Agent": "daily-papers-bot/1.0"})
            with urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            return body, ("ok" if attempt == 0 else "retry_recovered")
        except HTTPError as e:
            if e.code != 429 and e.code < 500:
                # Permanent client error — do not retry
                print(f"  [WARN] fetch failed {url}: HTTP {e.code}", file=sys.stderr)
                return "", f"failed: HTTP {e.code}"
            last_err = f"HTTP {e.code}"
        except (URLError, socket.timeout, TimeoutError) as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:120]}"

        if attempt < retries:
            backoff = _RETRY_BACKOFFS[min(attempt, len(_RETRY_BACKOFFS) - 1)]
            print(
                f"  [retry {attempt + 1}/{retries}] {url} failed ({last_err}); "
                f"sleeping {backoff}s",
                file=sys.stderr,
            )
            time.sleep(backoff)

    print(f"  [WARN] fetch failed after {attempts} attempt(s) {url}: {last_err}", file=sys.stderr)
    return "", f"failed: {last_err}"


def _parse_hf_item(item: dict, source: str) -> tuple[str, dict] | None:
    """Parse a single HF API item into (arxiv_id, paper_dict). Returns None on skip."""
    p = item.get("paper", {})
    arxiv_id = p.get("id", "")
    if not arxiv_id:
        return None

    upvotes = p.get("upvotes", 0)

    # Authors
    authors_raw = p.get("authors", [])
    if isinstance(authors_raw, list):
        names = []
        for a in authors_raw:
            if isinstance(a, dict):
                names.append(a.get("name", ""))
            elif isinstance(a, str):
                names.append(a)
        authors = ", ".join(n for n in names if n)
    else:
        authors = str(authors_raw)

    paper = {
        "title": p.get("title", ""),
        "authors": authors,
        "affiliations": "",
        "abstract": p.get("summary", ""),
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
        "date": (p.get("publishedAt") or "")[:10],
        "score": 0,
        "category": "",
        "source": source,
        "hf_upvotes": upvotes,
    }

    paper["score"] = score_paper(paper)

    if paper["score"] < 0:
        return None

    return arxiv_id, paper


_HF_BASE = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")


def fetch_hf_papers(start_date=None, end_date=None) -> tuple[list[dict], dict]:
    """Returns (papers, health). health.status ∈ {ok, partial, failed, skipped}."""
    papers = {}  # arxiv_id → paper
    days_attempted = 0
    days_succeeded = 0
    failures: list[dict] = []

    def _consume(endpoint: str, label: str) -> bool:
        """Fetch one HF endpoint and merge into papers. Returns True on success."""
        nonlocal failures
        raw, status = fetch_url(endpoint, retries=1)
        if status.startswith("failed"):
            failures.append({"label": label, "error": status.removeprefix("failed: ")})
            return False
        try:
            items = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            failures.append({"label": label, "error": "JSONDecodeError"})
            print(f"  [WARN] bad JSON from hf-daily {label}", file=sys.stderr)
            return False
        for item in items:
            result = _parse_hf_item(item, "hf-daily")
            if result:
                arxiv_id, paper = result
                if arxiv_id not in papers or paper["score"] > papers[arxiv_id]["score"]:
                    papers[arxiv_id] = paper
        return True

    # ── hf-daily: loop each day in range ──
    if start_date and end_date:
        d = start_date
        while d <= end_date:
            date_str = d.isoformat()
            endpoint = f"{_HF_BASE}/api/daily_papers?date={date_str}&limit=100"
            print(f"  Fetching hf-daily {date_str}...", file=sys.stderr)
            days_attempted += 1
            if _consume(endpoint, date_str):
                days_succeeded += 1
            d += timedelta(days=1)
    else:
        # Legacy single-call (days=1 default)
        endpoint = f"{_HF_BASE}/api/daily_papers?limit=50"
        print(f"  Fetching hf-daily...", file=sys.stderr)
        days_attempted += 1
        if _consume(endpoint, "today"):
            days_succeeded += 1

    result = list(papers.values())
    print(f"  HF: {len(result)} papers after scoring", file=sys.stderr)

    if days_attempted == 0:
        health_status = "skipped"
    elif days_succeeded == 0:
        health_status = "failed"
    elif days_succeeded < days_attempted:
        health_status = "partial"
    else:
        health_status = "ok"

    health = {
        "status": health_status,
        "days_attempted": days_attempted,
        "days_succeeded": days_succeeded,
    }
    if failures:
        health["failures"] = failures
    return result, health


# ── arXiv: RSS + /list/recent dual-source ──────────────────────────────────
#
# arXiv's official /api/query endpoint is unreachable from many networks
# (long-running timeout, not just rate-limiting). RSS feeds and HTML list
# pages on the same domain remain accessible. We use both:
#   - RSS feed (`/rss/{cat}`): full abstract, ~today only (~5-250 entries/cat)
#   - HTML list page (`/list/{cat}/recent`): last ~5 days, title only
# Multi-day mode uses both; single-day mode uses RSS only.

_NS_ATOM = "{http://www.w3.org/2005/Atom}"
_NS_ARXIV_RSS = "{http://arxiv.org/schemas/atom}"
_NS_DC = "{http://purl.org/dc/elements/1.1/}"

_LIST_DATE_HEADER_RE = re.compile(
    r"<h3>\s*(\w{3,9},?\s+\d{1,2}\s+\w{3,9}\s+\d{4})\s*\(", re.IGNORECASE
)
_LIST_DT_DD_BLOCK_RE = re.compile(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", re.DOTALL)
_LIST_ABS_HREF_RE = re.compile(r'href\s*=\s*"/abs/(\d{4}\.\d+)"')
_LIST_TITLE_DIV_RE = re.compile(
    r"<div class=['\"]list-title[^'\"]*['\"]>(.*?)</div>", re.DOTALL
)
_LIST_AUTHORS_DIV_RE = re.compile(
    r"<div class=['\"]list-authors['\"]>(.*?)</div>", re.DOTALL
)
_LIST_AUTHOR_LINK_RE = re.compile(r"<a[^>]*>([^<]+)</a>")
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


def _parse_rfc822_date(s: str):
    try:
        return parsedate_to_datetime(s).date()
    except (TypeError, ValueError):
        return None


def _parse_recent_list_date_header(s: str):
    """Parse e.g. 'Wed, 27 May 2026' → date."""
    for fmt in ("%a, %d %b %Y", "%A, %d %B %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _fetch_arxiv_rss_one(cat: str) -> tuple[list[dict], dict]:
    """Fetch one category's RSS feed. Returns (papers, health_per_endpoint)."""
    url = f"https://export.arxiv.org/rss/{cat}"
    body, status = fetch_url(url, timeout=15, retries=2)
    health = {"category": cat, "endpoint": "rss", "status": status}
    if status.startswith("failed"):
        return [], health

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        health["status"] = f"failed: XML parse: {e}"
        return [], health

    channel = root.find("channel")
    if channel is None:
        health["status"] = "failed: no <channel>"
        return [], health

    papers: list[dict] = []
    skipped_replace = 0
    for item in channel.findall("item"):
        announce_type_el = item.find(f"{_NS_ARXIV_RSS}announce_type")
        announce_type = announce_type_el.text if announce_type_el is not None else ""
        if announce_type == "replace":
            skipped_replace += 1
            continue

        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        pub_el = item.find("pubDate")
        creator_el = item.find(f"{_NS_DC}creator")

        if title_el is None or link_el is None:
            continue

        title = " ".join((title_el.text or "").split())
        link = (link_el.text or "").strip()
        arxiv_id = link.split("/abs/")[-1] if "/abs/" in link else ""

        # description body looks like:
        #   "arXiv:NNNN.NNNNN Announce Type: new  Abstract: ...real text..."
        desc = (desc_el.text or "").strip() if desc_el is not None else ""
        m = re.search(r"Abstract:\s*(.*)", desc, re.DOTALL)
        abstract = " ".join((m.group(1) if m else desc).split())

        authors = (creator_el.text or "").strip() if creator_el is not None else ""
        pub_date = _parse_rfc822_date((pub_el.text or "").strip()) if pub_el is not None else None

        paper = {
            "title": title,
            "authors": authors,
            "affiliations": "",
            "abstract": abstract,
            "url": link,
            "pdf": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
            "date": pub_date.isoformat() if pub_date else "",
            "score": 0,
            "category": cat,
            "source": "arxiv-rss",
            "announce_type": announce_type,
        }
        paper["score"] = score_paper(paper)
        if paper["score"] >= 0:
            papers.append(paper)

    health["items_kept"] = len(papers)
    health["skipped_replace"] = skipped_replace
    return papers, health


def _parse_list_html(body: str, cat: str, source_tag: str) -> list[dict]:
    """HTML parser for /list/{cat}/recent. Walks per-day <h3> headers
    ("Wed, 27 May 2026 (showing ...)") and the <dt>/<dd> entries beneath each.
    """
    sections = re.split(r"(<h3>[^<]*</h3>)", body)
    current_date = None
    papers: list[dict] = []
    for chunk in sections:
        if chunk.startswith("<h3>"):
            m = _LIST_DATE_HEADER_RE.search(chunk)
            current_date = _parse_recent_list_date_header(m.group(1)) if m else None
            continue
        for block in _LIST_DT_DD_BLOCK_RE.finditer(chunk):
            dt_html, dd_html = block.group(1), block.group(2)
            aid_m = _LIST_ABS_HREF_RE.search(dt_html)
            if not aid_m:
                continue
            arxiv_id = aid_m.group(1)

            title = ""
            tm = _LIST_TITLE_DIV_RE.search(dd_html)
            if tm:
                title = _TAG_STRIP_RE.sub("", tm.group(1)).strip()
                if title.lower().startswith("title:"):
                    title = title[6:].strip()
                title = " ".join(title.split())

            authors = ""
            am = _LIST_AUTHORS_DIV_RE.search(dd_html)
            if am:
                names = _LIST_AUTHOR_LINK_RE.findall(am.group(1))
                authors = ", ".join(n.strip() for n in names if n.strip())

            paper = {
                "title": title,
                "authors": authors,
                "affiliations": "",
                "abstract": "",  # not present on list page
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
                "date": current_date.isoformat() if current_date else "",
                "score": 0,
                "category": cat,
                "source": source_tag,
            }
            paper["score"] = score_paper(paper)
            if paper["score"] >= 0:
                papers.append(paper)
    return papers


def _fetch_arxiv_list_recent_one(cat: str) -> tuple[list[dict], dict]:
    """Fetch /list/{cat}/recent HTML and parse. Title-only (no abstract)."""
    # ?skip=0&show=2000 disables pagination — without this, days at the
    # edge of the 5-day window get cut to "showing first N of M entries".
    url = f"https://arxiv.org/list/{cat}/recent?skip=0&show=2000"
    body, status = fetch_url(url, timeout=20, retries=2)
    health = {"category": cat, "endpoint": "list-recent", "status": status}
    if status.startswith("failed"):
        return [], health
    papers = _parse_list_html(body, cat, source_tag="arxiv-list")
    health["items_kept"] = len(papers)
    return papers, health


def _parallel_fetch(fn, categories: list[str], max_workers: int = 3):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fn, cat): cat for cat in categories}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                cat = futures[fut]
                results.append(
                    ([], {"category": cat, "status": f"failed: {type(e).__name__}: {e}"})
                )
    return results


def fetch_arxiv_papers(start_date=None, end_date=None, days: int = 1) -> tuple[list[dict], dict]:
    """Fetch arXiv via RSS (always) + /list/recent (multi-day mode).

    - Single-day (days == 1): RSS only — full title + abstract.
    - Multi-day  (days > 1):  RSS + /list/recent.
      /list/recent papers have title only (no abstract), so they score
      against title-keyword hits only. /recent covers ~5 working days —
      for windows beyond that, the older portion simply isn't covered
      (strict policy: don't pad with month-page papers that lack date).

    Returns (papers, health).
    """
    print(
        f"  Fetching arXiv: RSS x{len(ARXIV_CATEGORIES)}"
        + (f" + /list/recent x{len(ARXIV_CATEGORIES)}" if days > 1 else "")
        + " (parallel)...",
        file=sys.stderr,
    )

    rss_results = _parallel_fetch(_fetch_arxiv_rss_one, ARXIV_CATEGORIES)
    rss_papers: list[dict] = []
    rss_health: list[dict] = []
    for papers, h in rss_results:
        rss_papers.extend(papers)
        rss_health.append(h)
    print(
        f"  RSS: {len(rss_papers)} scored papers across {len(ARXIV_CATEGORIES)} cats",
        file=sys.stderr,
    )

    list_papers: list[dict] = []
    list_health: list[dict] = []
    if days > 1:
        list_results = _parallel_fetch(_fetch_arxiv_list_recent_one, ARXIV_CATEGORIES)
        for papers, h in list_results:
            list_papers.extend(papers)
            list_health.append(h)
        print(
            f"  /recent: {len(list_papers)} scored papers across {len(ARXIV_CATEGORIES)} cats",
            file=sys.stderr,
        )

    # Merge by arxiv_id; prefer entries that have abstract (RSS) over title-only (/recent)
    by_id: dict[str, dict] = {}
    for p in rss_papers + list_papers:
        aid = extract_arxiv_id(p["url"])
        if not aid:
            continue
        existing = by_id.get(aid)
        if existing is None:
            by_id[aid] = p
        elif not existing.get("abstract") and p.get("abstract"):
            by_id[aid] = p

    # Date filter (multi-day mode only — same policy as before)
    filtered_by_date = 0
    final_papers: list[dict] = []
    for p in by_id.values():
        date_str = p.get("date", "")
        if days > 1 and start_date and end_date and date_str:
            try:
                pub_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if pub_date < start_date or pub_date > end_date:
                    filtered_by_date += 1
                    continue
            except ValueError:
                pass
        final_papers.append(p)

    print(
        f"  arXiv combined: {len(final_papers)} unique papers "
        f"(RSS {len(rss_papers)} + /recent {len(list_papers)}, "
        f"{filtered_by_date} filtered by date)",
        file=sys.stderr,
    )

    # Aggregate health across all endpoints
    all_health = rss_health + list_health
    failures = [h for h in all_health if h["status"].startswith("failed")]
    if not all_health:
        overall_status = "skipped"
    elif len(failures) == len(all_health):
        overall_status = "failed"
    elif failures:
        overall_status = "partial"
    elif any(h["status"] == "retry_recovered" for h in all_health):
        overall_status = "retry_recovered"
    else:
        overall_status = "ok"

    health: dict = {
        "status": overall_status,
        "endpoints_attempted": len(all_health),
        "endpoints_failed": len(failures),
        "rss_kept": len(rss_papers),
        "list_recent_kept": len(list_papers),
        "scored_unique_count": len(final_papers),
        "filtered_by_date": filtered_by_date,
    }
    if failures:
        health["failures"] = [
            {"cat": h["category"], "endpoint": h["endpoint"], "error": h["status"]}
            for h in failures[:10]
        ]

    return final_papers, health


# ── Merge & Dedup ──────────────────────────────────────────────────────────




def load_history() -> list[dict]:
    return _history_store.load()


def load_fallback_ids(days: int = 7) -> set[str]:
    ids: set[str] = set()
    today = datetime.now().date()
    for d in range(1, days + 1):
        fpath = DAILYPAPERS_DIR / f"{(today - timedelta(days=d)).isoformat()}-论文推荐.md"
        if fpath.exists():
            try:
                text = fpath.read_text()
                ids.update(extract_all_ids(text))
            except IOError:
                pass
    return ids


def merge_and_dedup(
    hf_papers: list[dict],
    arxiv_papers: list[dict],
    target_date,
    days: int = 1,
    top_n: int = TOP_N,
) -> list[dict]:
    # ── age filter ──
    # Strict policy: window matches requested days exactly, capped by MAX_AGE_DAYS ceiling.
    # "max_age_days is the user's bottom line — never relax it to pad volume."
    #   --days 1 → window=1 (target_date only; "今日推荐"严格今天 published)
    #   --days 3 → window=3 (last 3 days inclusive)
    #   --days 7 → window=min(7, MAX_AGE_DAYS)
    # Papers with unknown date are dropped — can't verify in-window, don't risk
    # smuggling stale papers in via sources that don't carry per-paper date.
    age_window = min(max(days, 1), MAX_AGE_DAYS)
    age_cutoff = target_date - timedelta(days=age_window - 1)  # inclusive lower bound
    aged_out = 0
    no_date_dropped = 0
    age_filtered: list[dict] = []
    # 收集 search meta（供 review 阶段写入日报 frontmatter）
    stats: dict = {
        "target_date": target_date.isoformat(),
        "days_window": days,
        "age_cutoff": age_cutoff.isoformat(),
        "age_window_days": age_window,
        "source_counts": {
            "hf": len(hf_papers),
            "arxiv": len(arxiv_papers),
        },
        "filter_steps": {},
    }
    for p in hf_papers + arxiv_papers:
        pub_str = (p.get("date") or "").strip()
        if not pub_str:
            no_date_dropped += 1
            continue
        try:
            pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
        except ValueError:
            no_date_dropped += 1
            continue
        if age_cutoff <= pub_date <= target_date:
            age_filtered.append(p)
            continue
        aged_out += 1
    print(
        f"  Age filter ({age_cutoff}..{target_date}, window={age_window}d): "
        f"kept {len(age_filtered)} / dropped {aged_out} aged + {no_date_dropped} no-date",
        file=sys.stderr,
    )
    stats["filter_steps"]["age_filter"] = {
        "kept": len(age_filtered),
        "dropped_aged": aged_out,
        "dropped_no_date": no_date_dropped,
    }

    # ── merge by arXiv ID, keep higher score ──
    by_id: dict[str, dict] = {}
    for p in age_filtered:
        aid = extract_arxiv_id(p["url"])
        if not aid:
            continue
        if aid not in by_id or p["score"] > by_id[aid]["score"]:
            by_id[aid] = p

    print(f"  Merged: {len(by_id)} unique papers", file=sys.stderr)
    stats["filter_steps"]["merged_unique"] = len(by_id)

    if days > 1:
        # ── multi-day mode: skip history dedup ──
        # User explicitly wants to see all N days, don't filter out previously recommended
        print(f"  Multi-day mode (days={days}): skipping history dedup", file=sys.stderr)
        candidates = [p for p in by_id.values() if p["score"] >= MIN_SCORE]
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:top_n]
        print(f"  Final: {len(top)} papers (top_n={top_n})", file=sys.stderr)
        stats["filter_steps"]["history_dedup"] = "skipped (multi-day mode)"
        stats["filter_steps"]["min_score_filter"] = {"min_score": MIN_SCORE, "kept": len(candidates)}
        stats["final_count"] = len(top)
        return top, stats

    # ── single-day mode: history dedup as before ──
    history = load_history()
    history_ids: dict[str, str] = {}  # id → earliest date
    for h in history:
        hid, hdate = h.get("id", ""), h.get("date", "")
        if hid and hdate:
            if hid not in history_ids or hdate < history_ids[hid]:
                history_ids[hid] = hdate

    if len(history) < 10:
        for fid in load_fallback_ids():
            history_ids.setdefault(fid, "unknown")

    # ── cross-day dedup ──
    deduped: dict[str, dict] = {}
    removed = 0
    for aid, p in by_id.items():
        if aid in history_ids:
            removed += 1
        else:
            deduped[aid] = p

    # Mark any remaining that appear in history
    for aid, p in deduped.items():
        if aid in history_ids and not p.get("is_re_recommend"):
            p["is_re_recommend"] = True
            p["last_recommend_date"] = history_ids[aid]

    print(f"  After history dedup: {len(deduped)} (removed {removed})", file=sys.stderr)
    stats["filter_steps"]["history_dedup"] = {
        "kept": len(deduped),
        "removed_already_recommended": removed,
    }

    # ── filter + sort ──
    candidates = [p for p in deduped.values() if p["score"] >= MIN_SCORE]
    candidates.sort(key=lambda x: x["score"], reverse=True)
    stats["filter_steps"]["min_score_filter"] = {"min_score": MIN_SCORE, "kept": len(candidates)}

    # Back-fill from history if pool is thin
    backfill_count = 0
    if len(candidates) < 20 and removed > 0:
        backfill = []
        for aid, p in by_id.items():
            if aid not in deduped and p["score"] >= MIN_SCORE:
                p["is_re_recommend"] = True
                p["last_recommend_date"] = history_ids.get(aid, "unknown")
                backfill.append(p)
        backfill.sort(key=lambda x: x["score"], reverse=True)
        needed = 20 - len(candidates)
        candidates.extend(backfill[:needed])
        backfill_count = len(backfill[:needed])
        if backfill[:needed]:
            print(f"  Back-filled {min(needed, len(backfill))} from history", file=sys.stderr)
    stats["filter_steps"]["history_backfilled"] = backfill_count

    top = candidates[:top_n]
    print(f"  Final: {len(top)} papers", file=sys.stderr)
    stats["final_count"] = len(top)
    return top, stats


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--days", type=int, default=1, help="Number of days to fetch (default: 1)")
    args = parser.parse_args()

    target_date = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date
        else datetime.now().date()
    )
    days = max(1, args.days)
    start_date = target_date - timedelta(days=days - 1)
    top_n = TOP_N * days

    is_weekend = target_date.weekday() >= 5
    print(
        f"[fetch_and_score] {target_date} ({'weekend' if is_weekend else 'weekday'})"
        + (f", days={days} [{start_date} ~ {target_date}], top_n={top_n}" if days > 1 else ""),
        file=sys.stderr,
    )

    hf_papers, hf_health = fetch_hf_papers(start_date, target_date)
    arxiv_papers, arxiv_health = fetch_arxiv_papers(start_date, target_date, days)
    top, stats = merge_and_dedup(hf_papers, arxiv_papers, target_date, days=days, top_n=top_n)

    # 写一份 search meta 到 /tmp，供 review skill 读取以加进日报 frontmatter
    from user_config import temp_file_path
    meta = {
        **stats,
        "config": {
            "arxiv_categories": ARXIV_CATEGORIES,
            "keywords_count": len(KEYWORDS),
            "negative_keywords_count": len(NEGATIVE_KEYWORDS),
            "domain_boost_count": len(DOMAIN_BOOST_KEYWORDS),
            "top_n": TOP_N,
            "min_score": MIN_SCORE,
            "max_age_days": MAX_AGE_DAYS,
        },
        "source_breakdown_of_final": {
            s: sum(1 for p in top if p.get("source") == s)
            for s in {"hf-daily", "arxiv"}
        },
        "api_health": {
            "arxiv": arxiv_health,
            "hf_daily": hf_health,
        },
    }
    meta_path = temp_file_path("daily_papers_search_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  Search meta saved: {meta_path}", file=sys.stderr)

    # Output to stdout (UTF-8 encoded for Windows compatibility)
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    json.dump(top, sys.stdout, ensure_ascii=False, indent=2)
    print(file=sys.stdout)  # trailing newline


if __name__ == "__main__":
    main()
