#!/usr/bin/env python3
"""pipeline_guard.py — spec #3: mechanical Phase 5.5 enforcement.

Runs 3 hard-fact checks on a draft daily-paper report:
  C1 date_cutoff: every recommended paper.published_date >= meta.age_cutoff
  C2 existing_note_wikilink: every `📒 **已有笔记**: [[xxx]]` resolves to a .md file
  C3 critique_evidence_triples: every non-existing-note paper section has
     `🧪 锐评依据` block with >= 2 `Claim/Evidence/Confidence` triples

CLI:
  pipeline_guard.py <draft.md> --enriched <path> --meta <path>
                               --notes <dir>     --json-out <path>

Exit codes:
  0 — all checks passed
  1 — at least 1 violation
  2 — guard internal error (missing input, JSON parse, etc.)

Outputs:
  stdout: silent (unless --verbose)
  stderr: 1-line summary
  --json-out: full report (see spec §4.4 for schema)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ARXIV_ID_RE = re.compile(r"arxiv\.org/abs/(\d{4}\.\d{4,5})")
PAPER_SECTION_RE = re.compile(r"^### (\d+)\.\s*(.+)$", re.MULTILINE)
EXISTING_NOTE_MARKER_RE = re.compile(r"📒\s*\*\*已有笔记\*\*\s*:\s*\[\[([^\]]+)\]\]")
TRIPLE_BLOCK_HEADER_RE = re.compile(r"🧪[\s\*]*锐评依据")
TRIPLE_LINE_RE = re.compile(
    r"`Claim:[^`]*`\s*\|\s*`Evidence:[^`]*`\s*\|\s*`Confidence:[^`]*`"
)

MAX_DRAFT_BYTES = 5 * 1024 * 1024


def split_paper_sections(draft: str) -> list[dict]:
    """Split draft into per-paper sections.

    Returns list of {index, header, title, content, line_start, line_end}.
    """
    matches = list(PAPER_SECTION_RE.finditer(draft))
    sections = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(draft)
        section_text = draft[start:end]
        line_start = draft[:start].count("\n") + 1
        line_end = line_start + section_text.count("\n")
        sections.append({
            "index": int(m.group(1)),
            "header": m.group(0),
            "title": m.group(2).strip(),
            "content": section_text,
            "line_start": line_start,
            "line_end": line_end,
        })
    return sections


def is_existing_note_paper(section_content: str) -> bool:
    return bool(EXISTING_NOTE_MARKER_RE.search(section_content))


def extract_arxiv_id(section_content: str) -> str | None:
    m = ARXIV_ID_RE.search(section_content)
    return m.group(1) if m else None


def check_date_cutoff(
    sections: list[dict],
    enriched_by_id: dict[str, dict],
    age_cutoff,
) -> tuple[list[dict], int, int]:
    """C1: every paper.published_date >= age_cutoff.

    Skips papers with no arxiv id (LLM forgot link) and papers with no
    enrichment data (paper not in fetch pool — already a different bug).
    """
    violations: list[dict] = []
    skipped_no_id = 0
    skipped_no_data = 0
    for s in sections:
        aid = extract_arxiv_id(s["content"])
        if not aid:
            skipped_no_id += 1
            continue
        if aid not in enriched_by_id:
            skipped_no_data += 1
            continue
        date_str = (enriched_by_id[aid].get("date") or "")[:10]
        if not date_str:
            continue
        try:
            pub = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if pub < age_cutoff:
            violations.append({
                "check": "date_cutoff",
                "severity": "error",
                "paper_arxiv_id": aid,
                "paper_title": s["title"],
                "paper_published_date": date_str,
                "age_cutoff": age_cutoff.isoformat(),
                "draft_section_header": s["header"],
                "draft_line": s["line_start"],
                "fix_hint": (
                    f"Remove paper #{s['index']} ({s['title'][:40]}) — "
                    f"published {date_str} is older than age_cutoff "
                    f"{age_cutoff.isoformat()}. Move it to '被排除的论文' "
                    f"section if relevant."
                ),
            })
    return violations, skipped_no_id, skipped_no_data


def check_existing_note_wikilinks(
    draft: str, notes_path: Path
) -> tuple[list[dict], int]:
    """C2: every `📒 **已有笔记**: [[xxx]]` resolves to {notes}/**/xxx.md."""
    violations: list[dict] = []
    checked = 0
    for m in EXISTING_NOTE_MARKER_RE.finditer(draft):
        wikilink = m.group(1).strip()
        checked += 1
        matches = list(notes_path.rglob(f"{wikilink}.md"))
        if not matches:
            line_no = draft[:m.start()].count("\n") + 1
            violations.append({
                "check": "existing_note_wikilink",
                "severity": "error",
                "wikilink": wikilink,
                "scanned_dir": str(notes_path),
                "draft_line": line_no,
                "fix_hint": (
                    f"Remove the line containing "
                    f"`📒 **已有笔记**: [[{wikilink}]]` — no file matches "
                    f"at {notes_path}"
                ),
            })
    return violations, checked


def check_critique_triples(
    sections: list[dict],
) -> tuple[list[dict], int]:
    """C3: every non-existing-note paper section needs `🧪 锐评依据` block
    with >= 2 `Claim/Evidence/Confidence` triples.

    Papers with `📒 **已有笔记**: [[xxx]]` marker use a simplified format
    and are skipped (the existing note carries the deep analysis).
    """
    violations: list[dict] = []
    skipped = 0
    for s in sections:
        if is_existing_note_paper(s["content"]):
            skipped += 1
            continue
        header_match = TRIPLE_BLOCK_HEADER_RE.search(s["content"])
        triple_count = 0
        if header_match:
            after_header = s["content"][header_match.end():]
            triple_count = len(TRIPLE_LINE_RE.findall(after_header))
        if triple_count < 2:
            violations.append({
                "check": "critique_evidence_triples",
                "severity": "error",
                "paper_section_header": s["header"],
                "draft_line_start": s["line_start"],
                "draft_line_end": s["line_end"],
                "triple_count": triple_count,
                "minimum_required": 2,
                "fix_hint": (
                    f"Add at least {2 - triple_count} more "
                    f"`Claim/Evidence/Confidence` entry under the "
                    f"🧪 锐评依据 block of paper #{s['index']}."
                ),
            })
    return violations, skipped


def _die(msg: str, code: int = 2) -> None:
    print(f"guard: error: {msg}", file=sys.stderr)
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description="pipeline_guard for daily papers review")
    parser.add_argument("draft", help="path to draft markdown")
    parser.add_argument("--enriched", required=True, help="path to enriched.json")
    parser.add_argument("--meta", required=True, help="path to search_meta.json")
    parser.add_argument("--notes", required=True, help="path to paper notes root")
    parser.add_argument("--json-out", required=True, help="path to write JSON report")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    draft_path = Path(args.draft)
    enriched_path = Path(args.enriched)
    meta_path = Path(args.meta)
    notes_path = Path(args.notes)
    json_out_path = Path(args.json_out)

    for p, label in [
        (draft_path, "draft"),
        (enriched_path, "enriched"),
        (meta_path, "meta"),
        (notes_path, "notes"),
    ]:
        if not p.exists():
            _die(f"{label} not found: {p}", code=2)

    if draft_path.stat().st_size > MAX_DRAFT_BYTES:
        _die(f"draft too large (> 5 MB): {draft_path}", code=2)

    try:
        draft = draft_path.read_text(encoding="utf-8")
    except OSError as e:
        _die(f"cannot read draft: {e}", code=2)
    try:
        enriched = json.loads(enriched_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _die(f"enriched JSON: {e}", code=2)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _die(f"meta JSON: {e}", code=2)

    cutoff_str = meta.get("age_cutoff")
    if not cutoff_str:
        _die("meta has no age_cutoff", code=2)
    try:
        age_cutoff = datetime.strptime(cutoff_str, "%Y-%m-%d").date()
    except ValueError:
        _die(f"meta.age_cutoff not YYYY-MM-DD: {cutoff_str}", code=2)

    enriched_by_id: dict[str, dict] = {}
    for p in enriched:
        m = ARXIV_ID_RE.search(p.get("url", ""))
        if m:
            enriched_by_id[m.group(1)] = p

    sections = split_paper_sections(draft)
    existing_note_count = sum(1 for s in sections if is_existing_note_paper(s["content"]))

    # Checks
    c1_violations, c1_skipped_no_id, c1_skipped_no_data = check_date_cutoff(
        sections, enriched_by_id, age_cutoff
    )
    c2_violations, c2_checked = check_existing_note_wikilinks(draft, notes_path)
    c3_violations, c3_skipped = check_critique_triples(sections)

    all_violations = c1_violations + c2_violations + c3_violations

    report = {
        "passed": len(all_violations) == 0,
        "draft_path": str(draft_path),
        "enriched_path": str(enriched_path),
        "meta_path": str(meta_path),
        "notes_path": str(notes_path),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_violations": len(all_violations),
            "by_check": {
                "date_cutoff": len(c1_violations),
                "existing_note_wikilink": len(c2_violations),
                "critique_evidence_triples": len(c3_violations),
            },
            "stats": {
                "papers_in_draft": len(sections),
                "papers_with_existing_note_marker": existing_note_count,
                "papers_skipped_for_C3": c3_skipped,
                "wikilinks_checked": c2_checked,
                "papers_skipped_no_arxiv_id": c1_skipped_no_id,
                "papers_no_enrichment_data": c1_skipped_no_data,
            },
        },
        "violations": all_violations,
    }

    json_out_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if report["passed"]:
        print("guard: passed", file=sys.stderr)
        sys.exit(0)
    s = report["summary"]["by_check"]
    print(
        f"guard: {len(all_violations)} violations "
        f"(date_cutoff={s['date_cutoff']}, "
        f"existing_note_wikilink={s['existing_note_wikilink']}, "
        f"critique_evidence_triples={s['critique_evidence_triples']}) — "
        f"see {json_out_path}",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
