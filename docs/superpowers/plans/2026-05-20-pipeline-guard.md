# pipeline_guard.py + Phase 5.5 Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `skills/_shared/pipeline_guard.py` — a stdlib-only Python tool that mechanically enforces 3 hard-fact checks (C1 date_cutoff, C2 existing_note_wikilink, C3 critique_evidence_triples) on draft daily-paper reports. Update `daily-papers-review/SKILL.md` so Phase 5.5 calls the guard and Phase 5.6 handles 1 round of LLM self-revision on failure.

**Architecture:** TDD inside-out. Write 6 fixture markdowns + 7 failing tests first, then implement guard incrementally (skeleton → C1 → C2 → C3), watching tests flip from FAIL to PASS at each step. Guard is a pure CLI: stdin draft + 3 path args + 1 output path → JSON report + exit code (0 pass / 1 violations / 2 guard error). Then update review SKILL.md prose and verify end-to-end against a simulated 2026-05-19 retrofit draft.

**Tech Stack:**
- Python 3 stdlib only (argparse, re, json, datetime, pathlib, sys)
- No pytest dependency — same PASS/FAIL/sys.exit pattern as `scripts/test_fetch_no_trending.py` (spec #1)
- Git (post-spec #0 repo at `~/DailyPaper/`)
- bash subprocess in tests (call guard CLI via `subprocess.run`)

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-pipeline-guard-design.md`

---

## File Structure

**Files to CREATE:**

| Path | Purpose | Approx lines |
|---|---|---|
| `skills/_shared/pipeline_guard.py` | Main guard (CLI + 3 checks + JSON report) | ~220 |
| `scripts/test_pipeline_guard.py` | 7 stdlib tests using subprocess | ~250 |
| `scripts/fixtures/enriched.json` | Shared enriched data covering all draft arxiv IDs | ~80 |
| `scripts/fixtures/meta.json` | Shared meta with age_cutoff=2026-05-13 | ~15 |
| `scripts/fixtures/notes/RealNote.md` | Empty stub; backs the [[RealNote]] wikilink in passing/skip fixtures | 1 |
| `scripts/fixtures/notes/SemaVoice.md` | Empty stub; backs another wikilink | 1 |
| `scripts/fixtures/draft_passing.md` | 2 papers, all checks pass | ~50 |
| `scripts/fixtures/draft_date_violation.md` | 1 paper with date 2025-08-15 (before cutoff 2026-05-13) | ~25 |
| `scripts/fixtures/draft_wikilink_missing.md` | Has `📒 **已有笔记**: [[FakeNote]]` (no such file) | ~25 |
| `scripts/fixtures/draft_triple_missing.md` | Paper with only 1 `Claim/Evidence/Confidence` triple | ~25 |
| `scripts/fixtures/draft_skip_existing_note.md` | Paper with `📒 **已有笔记**: [[RealNote]]` and no 🧪 block (C3 should skip) | ~20 |
| `scripts/fixtures/draft_combined.md` | All 3 violations together | ~60 |
| `scripts/fixtures/draft_retrofit_2026-05-19.md` | End-to-end fixture mimicking the historical 2026-05-19 leak (3 old papers) | ~80 |
| `docs/superpowers/plans/2026-05-20-pipeline-guard-COMPLETION.md` | Acceptance record (written in last task) | ~50 |

**Files to MODIFY:**

| Path | Change |
|---|---|
| `skills/daily-papers-review/SKILL.md` | Replace Phase 5.5 prose with "call pipeline_guard.py"; add new Phase 5.6 self-revision; update Phase 5.5.5 to render guard report verbatim instead of LLM hand-writing |

**Files NOT MODIFIED:**
- `skills/_shared/user_config.py` (guard doesn't use it; standalone)
- Other skill files (paper-reader, notes, weekly, compare, highlights, library-import, generate-mocs, daily-papers, daily-papers-fetch, daily-papers-notes)
- `fetch_and_score.py`, `enrich_papers.py`, etc.
- `scripts/test_fetch_no_trending.py` (spec #1 baseline — must still 7/7 PASS)
- Historical daily reports under `DailyPaper/DailyPapers/`

---

## Task 1: Pre-flight + create fixtures directory

**Files:**
- Verify-only (no writes yet)

- [ ] **Step 1: Verify spec #1 baseline 7/7 PASS**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py
echo "exit=$?"
```

Expected: `7 / 7 passed` + `exit=0`. If not, STOP — baseline broken.

- [ ] **Step 2: Verify spec #0 git repo is clean**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git status --porcelain | wc -l
cd /Users/xiangshu/DailyPaper && git log --oneline | head -3
```

Expected: porcelain count `0`; log shows the 2 spec #0 commits (`spec #0 completion record` + `import paper system from ~/.claude/skills/`).

- [ ] **Step 3: Confirm target paths do NOT exist yet**

Run:
```bash
ls /Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py 2>&1 | head -1
ls /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py 2>&1 | head -1
ls /Users/xiangshu/DailyPaper/scripts/fixtures/ 2>&1 | head -1
```

Expected: all three report "No such file or directory". If any exists non-empty, STOP and confirm with user.

- [ ] **Step 4: Create the fixtures directory tree**

Run:
```bash
mkdir -p /Users/xiangshu/DailyPaper/scripts/fixtures/notes
ls -la /Users/xiangshu/DailyPaper/scripts/fixtures/
```

Expected: `notes/` subdir exists; parent fixtures/ exists.

---

## Task 2: Write 6 fixture markdowns + shared enriched/meta JSON + 2 stub notes

⚠️ Fixtures must be written BEFORE tests, otherwise tests have nothing to run against. Each fixture's arxiv IDs must align with `enriched.json` entries.

**Files:**
- Create: 6 draft `.md` + `enriched.json` + `meta.json` + 2 stub notes (+1 retrofit draft used by Task 10)

- [ ] **Step 1: Write shared `enriched.json` covering all arxiv IDs**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/enriched.json` with EXACTLY this content:

```json
[
  {
    "title": "PassingPaper One",
    "url": "https://arxiv.org/abs/2605.10000",
    "date": "2026-05-15",
    "source": "arxiv",
    "score": 5,
    "abstract": "A speech synthesis approach.",
    "method_summary": "Uses Flow Matching for TTS.",
    "method_names": ["FlowMatching"],
    "section_headers": ["Introduction", "Method", "Experiments", "Ablation Study"],
    "captions": [],
    "has_real_world": false,
    "figure_url": "",
    "affiliations": "",
    "authors": "Alice, Bob"
  },
  {
    "title": "PassingPaper Two",
    "url": "https://arxiv.org/abs/2605.10001",
    "date": "2026-05-18",
    "source": "hf-daily",
    "score": 4,
    "abstract": "A speech LLM approach.",
    "method_summary": "Builds on EnCodec tokens.",
    "method_names": ["EnCodec", "SpeechLLM"],
    "section_headers": ["Introduction", "Approach", "Results"],
    "captions": [],
    "has_real_world": true,
    "figure_url": "",
    "affiliations": "",
    "authors": "Carol, Dave"
  },
  {
    "title": "VibeVoice Old Hit",
    "url": "https://arxiv.org/abs/2508.19205",
    "date": "2025-08-15",
    "source": "arxiv",
    "score": 6,
    "abstract": "An older but trending TTS paper.",
    "method_summary": "Old method.",
    "method_names": ["VibeVoice"],
    "section_headers": ["Introduction"],
    "captions": [],
    "has_real_world": false,
    "figure_url": "",
    "affiliations": "",
    "authors": "Eve"
  },
  {
    "title": "OmniFlatten Old",
    "url": "https://arxiv.org/abs/2410.05000",
    "date": "2024-10-10",
    "source": "arxiv",
    "score": 5,
    "abstract": "Very old full-duplex work.",
    "method_summary": "Old.",
    "method_names": ["OmniFlatten"],
    "section_headers": ["Method"],
    "captions": [],
    "has_real_world": false,
    "figure_url": "",
    "affiliations": "",
    "authors": "Frank"
  },
  {
    "title": "MiniCPM-o-4.5 Spring 2026",
    "url": "https://arxiv.org/abs/2604.03000",
    "date": "2026-04-15",
    "source": "arxiv",
    "score": 4,
    "abstract": "A spring 2026 Omni model, just outside age window.",
    "method_summary": "Omni.",
    "method_names": ["MiniCPM-o"],
    "section_headers": ["Method"],
    "captions": [],
    "has_real_world": false,
    "figure_url": "",
    "affiliations": "",
    "authors": "Grace"
  }
]
```

- [ ] **Step 2: Write shared `meta.json` with age_cutoff = 2026-05-13**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/meta.json` with EXACTLY this content:

```json
{
  "target_date": "2026-05-20",
  "days_window": 1,
  "age_cutoff": "2026-05-13",
  "age_window_days": 7,
  "source_counts": {"hf": 16, "arxiv": 100},
  "filter_steps": {
    "age_filter": {"kept": 30, "dropped_aged": 86},
    "merged_unique": 30,
    "history_dedup": {"kept": 28, "removed_already_recommended": 2},
    "min_score_filter": {"min_score": 2, "kept": 14},
    "history_backfilled": 0
  },
  "final_count": 14,
  "config": {
    "arxiv_categories": ["cs.SD", "eess.AS", "cs.CL"],
    "keywords_count": 44,
    "negative_keywords_count": 18,
    "domain_boost_count": 16,
    "top_n": 15,
    "min_score": 2,
    "max_age_days": 7
  },
  "source_breakdown_of_final": {"hf-daily": 5, "arxiv": 9}
}
```

- [ ] **Step 3: Write 2 stub note files for the wikilink check**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/notes/RealNote.md`:

```markdown
# RealNote

Stub for guard fixture; only filename matters.
```

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/notes/SemaVoice.md`:

```markdown
# SemaVoice

Stub for guard fixture; only filename matters.
```

- [ ] **Step 4: Write `draft_passing.md` (2 papers, all 3 checks should pass)**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/draft_passing.md` with this content:

```markdown
# 🔪 今日锐评

Two papers today, both reasonable.

## 分流表

| 等级 | 论文 |
|------|------|
| 👀 值得看 | [[PassingPaper]] · [[PassingPaper2]] |

---

## 🗣 TTS

### 1. PassingPaper One
- **链接**: [arXiv](https://arxiv.org/abs/2605.10000)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Reasonable. 👀
- **🧪 锐评依据**:
  - `Claim: TTS uses Flow Matching` | `Evidence: method_summary mentions Flow Matching` | `Confidence: 高`
  - `Claim: standard speech synthesis target` | `Evidence: abstract: A speech synthesis approach` | `Confidence: 高`

### 2. PassingPaper Two
- **链接**: [arXiv](https://arxiv.org/abs/2605.10001)
- **来源**: 📰 HF Daily，⬆️ 12
- **锐评**: Practical. 👀
- **🧪 锐评依据**:
  - `Claim: Uses EnCodec tokens` | `Evidence: method_summary mentions EnCodec` | `Confidence: 高`
  - `Claim: Speech-LLM angle` | `Evidence: method_names list contains SpeechLLM` | `Confidence: 中`
```

- [ ] **Step 5: Write `draft_date_violation.md` (1 old paper)**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/draft_date_violation.md`:

```markdown
# 🔪 今日锐评

A leaked old TTS paper got into today's recs.

## 分流表

| 等级 | 论文 |
|------|------|
| 🔥 必读 | [[VibeVoice]] |

---

## 🗣 TTS

### 1. VibeVoice Old Hit
- **链接**: [arXiv](https://arxiv.org/abs/2508.19205)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Allegedly strong, but this is an old paper. 🔥
- **🧪 锐评依据**:
  - `Claim: marketed as TTS SOTA` | `Evidence: abstract mentions TTS` | `Confidence: 高`
  - `Claim: this is an older paper` | `Evidence: date 2025-08-15 in enriched` | `Confidence: 高`
```

- [ ] **Step 6: Write `draft_wikilink_missing.md` (fake existing-note marker)**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/draft_wikilink_missing.md`:

```markdown
# 🔪 今日锐评

One paper with a hallucinated existing-note wikilink.

## 分流表

| 等级 | 论文 |
|------|------|
| 👀 值得看 | [[PassingPaper]] |

---

## 🗣 TTS

### 1. PassingPaper One
- **链接**: [arXiv](https://arxiv.org/abs/2605.10000)
- **来源**: 📄 arXiv 关键词检索
- 📒 **已有笔记**: [[FakeNote]]
```

- [ ] **Step 7: Write `draft_triple_missing.md` (only 1 triple)**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/draft_triple_missing.md`:

```markdown
# 🔪 今日锐评

One paper with insufficient evidence triples.

## 分流表

| 等级 | 论文 |
|------|------|
| 👀 值得看 | [[PassingPaper]] |

---

## 🗣 TTS

### 1. PassingPaper One
- **链接**: [arXiv](https://arxiv.org/abs/2605.10000)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Looks reasonable. 👀
- **🧪 锐评依据**:
  - `Claim: only one piece of evidence here` | `Evidence: abstract mentions TTS` | `Confidence: 高`
```

- [ ] **Step 8: Write `draft_skip_existing_note.md` (C3 should skip)**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/draft_skip_existing_note.md`:

```markdown
# 🔪 今日锐评

One existing-note paper with no triple block — C3 should skip it.

## 分流表

| 等级 | 论文 |
|------|------|
| 👀 值得看 | [[RealNote]] |

---

## 🗣 TTS

### 1. PassingPaper One
- **链接**: [arXiv](https://arxiv.org/abs/2605.10000)
- **来源**: 📄 arXiv 关键词检索
- 📒 **已有笔记**: [[RealNote]]
```

- [ ] **Step 9: Write `draft_combined.md` (all 3 violations)**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/draft_combined.md`:

```markdown
# 🔪 今日锐评

A draft with 3 different violations at once.

## 分流表

| 等级 | 论文 |
|------|------|
| 🔥 必读 | [[VibeVoice]] · [[FakeNote]] |
| 👀 值得看 | [[PassingPaper]] |

---

## 🗣 TTS

### 1. VibeVoice Old Hit
- **链接**: [arXiv](https://arxiv.org/abs/2508.19205)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Old paper leak. 🔥
- **🧪 锐评依据**:
  - `Claim: TTS focus` | `Evidence: abstract` | `Confidence: 高`
  - `Claim: old date` | `Evidence: 2025-08` | `Confidence: 高`

### 2. PassingPaper One
- **链接**: [arXiv](https://arxiv.org/abs/2605.10000)
- **来源**: 📄 arXiv 关键词检索
- 📒 **已有笔记**: [[FakeNote]]
- **锐评**: Has hallucinated note link. 👀
- **🧪 锐评依据**:
  - `Claim: TTS thing` | `Evidence: ok` | `Confidence: 高`
  - `Claim: another claim` | `Evidence: ok` | `Confidence: 中`

### 3. PassingPaper Two
- **链接**: [arXiv](https://arxiv.org/abs/2605.10001)
- **来源**: 📰 HF Daily，⬆️ 12
- **锐评**: Too few triples. 👀
- **🧪 锐评依据**:
  - `Claim: only one triple here` | `Evidence: abstract` | `Confidence: 高`
```

- [ ] **Step 10: Write `draft_retrofit_2026-05-19.md` (end-to-end fixture, all 3 historical leak papers)**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/fixtures/draft_retrofit_2026-05-19.md`:

```markdown
# 🔪 今日锐评

Simulated 2026-05-19 draft BEFORE the retrofit deletion — should contain 3 old papers that guard must flag.

## 分流表

| 等级 | 论文 |
|------|------|
| 🔥 必读 | [[VibeVoice]] · [[OmniFlatten]] · [[MiniCPM-o]] |
| 👀 值得看 | [[PassingPaper]] |

---

## 🗣 TTS

### 1. VibeVoice Old Hit
- **链接**: [arXiv](https://arxiv.org/abs/2508.19205)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Allegedly the new TTS SOTA. 🔥
- **🧪 锐评依据**:
  - `Claim: TTS focus` | `Evidence: abstract` | `Confidence: 高`
  - `Claim: claim of SOTA` | `Evidence: abstract` | `Confidence: 中`

### 2. OmniFlatten Old
- **链接**: [arXiv](https://arxiv.org/abs/2410.05000)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Full-duplex pioneer. 🔥
- **🧪 锐评依据**:
  - `Claim: full-duplex focus` | `Evidence: abstract` | `Confidence: 高`
  - `Claim: pioneering work` | `Evidence: abstract` | `Confidence: 中`

### 3. MiniCPM-o-4.5 Spring 2026
- **链接**: [arXiv](https://arxiv.org/abs/2604.03000)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Omni model, but just past window. 🔥
- **🧪 锐评依据**:
  - `Claim: Omni model` | `Evidence: abstract` | `Confidence: 高`
  - `Claim: spring 2026 release` | `Evidence: date 2026-04` | `Confidence: 高`

### 4. PassingPaper One
- **链接**: [arXiv](https://arxiv.org/abs/2605.10000)
- **来源**: 📄 arXiv 关键词检索
- **锐评**: Today's actual fresh paper. 👀
- **🧪 锐评依据**:
  - `Claim: TTS topic` | `Evidence: abstract` | `Confidence: 高`
  - `Claim: in-window paper` | `Evidence: date 2026-05-15` | `Confidence: 高`
```

- [ ] **Step 11: Sanity check all fixture files written**

Run:
```bash
ls -la /Users/xiangshu/DailyPaper/scripts/fixtures/
ls -la /Users/xiangshu/DailyPaper/scripts/fixtures/notes/
python3 -c "import json; print('enriched count:', len(json.load(open('/Users/xiangshu/DailyPaper/scripts/fixtures/enriched.json'))))"
python3 -c "import json; m=json.load(open('/Users/xiangshu/DailyPaper/scripts/fixtures/meta.json')); print('age_cutoff:', m['age_cutoff'])"
```

Expected: 7 `.md` files under fixtures/ (6 draft + 0 yet for notes); 2 files under notes/; enriched count == 5; age_cutoff == 2026-05-13.

Note: the count "7 .md" in `fixtures/` includes `draft_retrofit_2026-05-19.md` (used in Task 10), so total .md count in `fixtures/` is `draft_passing + draft_date_violation + draft_wikilink_missing + draft_triple_missing + draft_skip_existing_note + draft_combined + draft_retrofit_2026-05-19` = 7.

---

## Task 3: Write 7 failing tests

**Files:**
- Create: `/Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py`

- [ ] **Step 1: Create the test file**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py` with EXACTLY this content:

```python
#!/usr/bin/env python3
"""Tests for pipeline_guard.py (spec #3).

Runs each test as a subprocess against the real CLI, exactly as
daily-papers-review will invoke it. Stdlib only — no pytest.

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path("/Users/xiangshu/DailyPaper")
GUARD = REPO / "skills" / "_shared" / "pipeline_guard.py"
FIX = REPO / "scripts" / "fixtures"
ENRICHED = FIX / "enriched.json"
META = FIX / "meta.json"
NOTES = FIX / "notes"


def run_guard(draft_name: str, json_out: Path,
              enriched: Path = ENRICHED, meta: Path = META,
              notes: Path = NOTES) -> tuple[int, dict | None]:
    """Run guard and return (exit_code, parsed_report_or_None)."""
    cmd = [
        sys.executable, str(GUARD),
        str(FIX / draft_name),
        "--enriched", str(enriched),
        "--meta", str(meta),
        "--notes", str(notes),
        "--json-out", str(json_out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    report = None
    if json_out.exists():
        try:
            report = json.loads(json_out.read_text())
        except json.JSONDecodeError:
            pass
    return proc.returncode, report


def _tmp_json() -> Path:
    return Path(tempfile.mktemp(suffix=".json", prefix="guard_test_"))


def test_passing_draft():
    """All 3 checks pass — exit 0, no violations."""
    code, report = run_guard("draft_passing.md", _tmp_json())
    assert code == 0, f"expected exit 0, got {code}"
    assert report is not None, "no report written"
    assert report["passed"] is True
    assert report["summary"]["total_violations"] == 0


def test_date_cutoff_violation():
    """1 paper with date < cutoff → C1 violation."""
    code, report = run_guard("draft_date_violation.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    assert report["passed"] is False
    assert report["summary"]["by_check"]["date_cutoff"] >= 1
    dc = [v for v in report["violations"] if v["check"] == "date_cutoff"]
    assert dc, "no date_cutoff violation in report"
    assert dc[0]["paper_arxiv_id"] == "2508.19205"
    assert dc[0]["paper_published_date"] == "2025-08-15"
    assert dc[0]["age_cutoff"] == "2026-05-13"


def test_existing_note_wikilink_missing():
    """`📒 **已有笔记**: [[FakeNote]]` → C2 violation."""
    code, report = run_guard("draft_wikilink_missing.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    assert report["summary"]["by_check"]["existing_note_wikilink"] >= 1
    wk = [v for v in report["violations"] if v["check"] == "existing_note_wikilink"]
    assert wk, "no existing_note_wikilink violation in report"
    assert wk[0]["wikilink"] == "FakeNote"


def test_critique_triple_missing():
    """Paper with only 1 Claim/Evidence/Confidence triple → C3 violation."""
    code, report = run_guard("draft_triple_missing.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    assert report["summary"]["by_check"]["critique_evidence_triples"] >= 1
    tr = [v for v in report["violations"] if v["check"] == "critique_evidence_triples"]
    assert tr, "no critique_evidence_triples violation in report"
    assert tr[0]["triple_count"] == 1
    assert tr[0]["minimum_required"] == 2


def test_skip_existing_note_paper_for_c3():
    """Paper marked `📒 **已有笔记**: [[RealNote]]` + missing 🧪 block → C3 should SKIP, C2 should PASS (RealNote.md exists), exit 0."""
    code, report = run_guard("draft_skip_existing_note.md", _tmp_json())
    assert code == 0, f"expected exit 0, got {code}; violations={report.get('violations') if report else 'no report'}"
    assert report["summary"]["total_violations"] == 0
    assert report["summary"]["stats"]["papers_skipped_for_C3"] >= 1


def test_combined_violations():
    """All 3 violation types present → all 3 reported, exit 1."""
    code, report = run_guard("draft_combined.md", _tmp_json())
    assert code == 1, f"expected exit 1, got {code}"
    bc = report["summary"]["by_check"]
    assert bc["date_cutoff"] >= 1
    assert bc["existing_note_wikilink"] >= 1
    assert bc["critique_evidence_triples"] >= 1


def test_enriched_data_missing():
    """Missing enriched.json → exit 2 (guard error, not violation)."""
    bogus = Path("/tmp/__definitely_not_a_real_file__.json")
    if bogus.exists():
        bogus.unlink()
    code, report = run_guard("draft_passing.md", _tmp_json(), enriched=bogus)
    assert code == 2, f"expected exit 2 (guard error), got {code}"


TESTS = [
    test_passing_draft,
    test_date_cutoff_violation,
    test_existing_note_wikilink_missing,
    test_critique_triple_missing,
    test_skip_existing_note_paper_for_c3,
    test_combined_violations,
    test_enriched_data_missing,
]


def main():
    if not GUARD.exists():
        print(f"NOTE: {GUARD} does not exist — all tests will fail by design (TDD red phase).")
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
```

- [ ] **Step 2: Run tests — expect 7/7 FAIL (TDD red)**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py
echo "exit=$?"
```

Expected: every test FAIL or ERROR (subprocess can't find guard or the assertion about exit code mismatches because guard returns nonzero from missing file). exit=1.

If any test PASSes here against a nonexistent guard, the test is wrong — fix before proceeding.

---

## Task 4: Implement guard skeleton (CLI + IO + JSON; no checks yet)

Goal: argparse, input validation (exit 2 on missing files), empty `violations: []`, all-pass JSON output. After this task, `test_enriched_data_missing` PASSES; the 4 "violation" tests still FAIL (because their drafts have violations but guard reports `passed: true`); `test_passing_draft` and `test_skip_existing_note_paper_for_c3` PASS by accident.

**Files:**
- Create: `/Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py`

- [ ] **Step 1: Write the skeleton**

Use Write tool to create `/Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py` with this content:

```python
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
TRIPLE_BLOCK_HEADER_RE = re.compile(r"🧪\s*\*\*锐评依据\*\*")
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

    # Checks (no-op for now; populated in Tasks 5–7)
    c1_violations: list[dict] = []
    c1_skipped_no_id = 0
    c1_skipped_no_data = 0
    c2_violations: list[dict] = []
    c2_checked = 0
    c3_violations: list[dict] = []
    c3_skipped = 0

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
```

- [ ] **Step 2: Run tests — expect mixed PASS/FAIL**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py
echo "exit=$?"
```

Expected (4 PASS, 3 FAIL):
- PASS: test_passing_draft (no checks → passes anything)
- FAIL: test_date_cutoff_violation (skeleton returns 0; test wants 1)
- FAIL: test_existing_note_wikilink_missing (same)
- FAIL: test_critique_triple_missing (same)
- PASS: test_skip_existing_note_paper_for_c3 (no checks → passes)
- FAIL: test_combined_violations (same)
- PASS: test_enriched_data_missing (skeleton already does exit 2 on missing input)

exit=1.

If test_passing_draft FAILs at this stage, something is broken in the skeleton — debug before proceeding.

---

## Task 5: Implement C1 date_cutoff check

Goal: implement `check_date_cutoff()`. After this task, `test_date_cutoff_violation` PASSES.

**Files:**
- Modify: `/Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py`

- [ ] **Step 1: Add `check_date_cutoff` function above `main()`**

Use Edit tool to insert this function block right BEFORE the `def _die(` line:

`old_string`:
```
def _die(msg: str, code: int = 2) -> None:
```

`new_string`:
```
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


def _die(msg: str, code: int = 2) -> None:
```

- [ ] **Step 2: Wire C1 into `main()` — replace the no-op block**

Use Edit tool:

`old_string`:
```
    # Checks (no-op for now; populated in Tasks 5–7)
    c1_violations: list[dict] = []
    c1_skipped_no_id = 0
    c1_skipped_no_data = 0
    c2_violations: list[dict] = []
    c2_checked = 0
    c3_violations: list[dict] = []
    c3_skipped = 0
```

`new_string`:
```
    # Checks
    c1_violations, c1_skipped_no_id, c1_skipped_no_data = check_date_cutoff(
        sections, enriched_by_id, age_cutoff
    )
    c2_violations: list[dict] = []
    c2_checked = 0
    c3_violations: list[dict] = []
    c3_skipped = 0
```

- [ ] **Step 3: Run tests — expect 5 PASS / 2 FAIL**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py
echo "exit=$?"
```

Expected:
- PASS: test_passing_draft (no old papers in this draft)
- **PASS: test_date_cutoff_violation** (now C1 catches 2508.19205)
- FAIL: test_existing_note_wikilink_missing (C2 not implemented)
- FAIL: test_critique_triple_missing (C3 not implemented)
- PASS: test_skip_existing_note_paper_for_c3 (C3 not implemented → passes)
- FAIL: test_combined_violations (only date_cutoff caught, C2/C3 missing)
- PASS: test_enriched_data_missing

5 / 7 passed; exit=1.

If test_date_cutoff_violation still FAILs, inspect the JSON written by guard: `cat /tmp/guard_test_*.json | python3 -m json.tool` and check what arxiv id was extracted vs what enriched.json has.

---

## Task 6: Implement C2 existing_note_wikilink check

Goal: implement `check_existing_note_wikilinks()`. After this task, `test_existing_note_wikilink_missing` PASSES.

**Files:**
- Modify: `/Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py`

- [ ] **Step 1: Add `check_existing_note_wikilinks` function**

Use Edit tool to insert this function right BEFORE the `def _die(` line:

`old_string`:
```
def _die(msg: str, code: int = 2) -> None:
```

`new_string`:
```
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


def _die(msg: str, code: int = 2) -> None:
```

- [ ] **Step 2: Wire C2 into `main()`**

Use Edit tool:

`old_string`:
```
    c2_violations: list[dict] = []
    c2_checked = 0
```

`new_string`:
```
    c2_violations, c2_checked = check_existing_note_wikilinks(draft, notes_path)
```

- [ ] **Step 3: Run tests — expect 6 PASS / 1 FAIL**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py
echo "exit=$?"
```

Expected:
- PASS: test_passing_draft
- PASS: test_date_cutoff_violation
- **PASS: test_existing_note_wikilink_missing**
- FAIL: test_critique_triple_missing (C3 still not implemented)
- PASS: test_skip_existing_note_paper_for_c3 (C3 not implemented + RealNote.md exists)
- FAIL: test_combined_violations (C3 missing)
- PASS: test_enriched_data_missing

6 / 7 passed; exit=1.

---

## Task 7: Implement C3 critique_evidence_triples check

Goal: implement `check_critique_triples()`. After this task, all 7 tests PASS.

**Files:**
- Modify: `/Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py`

- [ ] **Step 1: Add `check_critique_triples` function**

Use Edit tool to insert this function right BEFORE the `def _die(` line:

`old_string`:
```
def _die(msg: str, code: int = 2) -> None:
```

`new_string`:
```
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
```

- [ ] **Step 2: Wire C3 into `main()`**

Use Edit tool:

`old_string`:
```
    c3_violations: list[dict] = []
    c3_skipped = 0
```

`new_string`:
```
    c3_violations, c3_skipped = check_critique_triples(sections)
```

- [ ] **Step 3: Run tests — expect 7/7 PASS (TDD green)**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py
echo "exit=$?"
```

Expected:
```
PASS: test_passing_draft
PASS: test_date_cutoff_violation
PASS: test_existing_note_wikilink_missing
PASS: test_critique_triple_missing
PASS: test_skip_existing_note_paper_for_c3
PASS: test_combined_violations
PASS: test_enriched_data_missing

7 / 7 passed
exit=0
```

If any FAIL, debug the specific check and re-run. Do not advance to Task 8 until 7/7.

---

## Task 8: Commit guard + tests + fixtures

**Files:**
- Stage and commit everything created so far in spec #3

- [ ] **Step 1: Stage explicit paths**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git add \
  skills/_shared/pipeline_guard.py \
  scripts/test_pipeline_guard.py \
  scripts/fixtures/
```

- [ ] **Step 2: Review staged list**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git status
```

Expected: "Changes to be committed" includes:
- `new file: skills/_shared/pipeline_guard.py`
- `new file: scripts/test_pipeline_guard.py`
- `new file: scripts/fixtures/enriched.json`
- `new file: scripts/fixtures/meta.json`
- `new file: scripts/fixtures/notes/RealNote.md`
- `new file: scripts/fixtures/notes/SemaVoice.md`
- 7 `new file: scripts/fixtures/draft_*.md` entries

Total ~13 new files. Working tree should be clean otherwise.

- [ ] **Step 3: Commit**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git commit -m "spec #3: pipeline_guard.py + 7 unit tests + 7 fixtures

Three hard-fact checks now mechanically enforced:
  C1 date_cutoff: published >= age_cutoff
  C2 existing_note_wikilink: 📒 已有笔记 [[xxx]] must resolve
  C3 critique_evidence_triples: ≥2 Claim/Evidence/Confidence per paper

stdlib only; subprocess-driven tests. 7/7 PASS.

🤖 Generated with Claude Code"
echo "exit=$?"
```

Expected: exit=0; commit summary shows ~13 files changed.

---

## Task 9: Update daily-papers-review/SKILL.md (Phase 5.5 + new 5.6)

Goal: replace the prose Phase 5.5 with a `pipeline_guard.py` invocation + add a new Phase 5.6 (LLM self-revision on guard fail) + change Phase 5.5.5 to render guard report verbatim instead of LLM hand-writing.

**Files:**
- Modify: `/Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md`

- [ ] **Step 1: Read the file around Phase 5.5 to confirm current state**

Use Read tool with `offset: 222, limit: 80` on `/Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md`. Locate the `### Phase 5.5:` heading and its 5 sub-sections (5.5.1 through 5.5.5).

- [ ] **Step 2: Replace Phase 5.5 prose with guard invocation + new 5.6**

Use Edit tool. The `old_string` is the entire Phase 5.5 block including all 5 sub-sections. Replace it as follows:

`old_string`:
```
### Phase 5.5: 对抗式自查（Adversarial Self-Review，**保存前强制做**）

**写完点评 → 不要直接进 Phase 6 保存**。先把刚生成的内容当**别人的草稿**读一遍，按下面 4 个维度逐项打分。**任何一项不通过，必须当场修订内容**再进 Phase 6。

> 灵感来源：Imbad0202/academic-research-skills 的 devils_advocate + integrity_verification 模式，但裁剪为单 agent 一遍过，避免日报变成论文 review。

#### 5.5.1 日期完整性（最高优先级——这是历史事故的重灾区）

- 读取 `/tmp/daily_papers_search_meta.json`，记下 `age_cutoff`
- 翻每一篇被收进推荐的论文，在 enriched 数据里看它的 `date` 字段
- 任何一篇 `date < age_cutoff` → **立刻从推荐表删掉**，理由写到「被排除的论文」节

#### 5.5.2 事实-证据校对

对每篇论文的「核心方法 / 对比方法 / 锐评 / 借鉴意义」做反向校验：

- **过度肯定检测**：搜出现「SOTA」「突破」「革命性」「最强」「首次」「全面超越」这种词的句子。每一处都要回到论文摘要 / method_summary / method_names 里找出**对应的具体数字或方法名**支撑；找不到的，要么补「（摘要未给硬数字，待全文确认）」要么删
- **凭空硬伤检测**：搜锐评里说论文「缺 ablation」「没 baseline 对比」「没流式」这种话。回 enriched 数据的 `section_titles` 和 `table_titles` 检查——如果章节标题里出现「Ablation Study」或表格标题出现「Comparison」，就说明你的指控是错的，必须撤销
- **已有笔记一致性**：如果某篇标为「已有笔记」`[[xxx]]`，必须 Glob `{NOTES_PATH}/**/xxx.md` 验证文件**真的存在**；不存在的 wikilink 要删
- **再推论文标注**：对 `is_re_recommend=true` 的论文，必须有「⏪ 再推提醒：这篇在 {last_recommend_date} 推荐过」一行

#### 5.5.3 Claim-Evidence 三元组覆盖

每篇非「已有笔记简化格式」的论文，必须有 `🧪 锐评依据` 块，且至少 2 条 `Claim/Evidence/Confidence`。漏了的补上。

#### 5.5.4 自相矛盾扫描

- 同一篇的「借鉴意义」说「很有用」+ 锐评说「没价值」→ 选一个，删另一个
- 分流表里写「🔥 必读」+ 锐评结尾打 `💀` 或 `🤡` → 等级要么降为「👀 值得看」要么改 emoji
- 开头总评说「今天 TTS 在爆发」+ 实际只有 1 篇 TTS → 收口，改总评

#### 5.5.5 输出自查结果

修订完后，在收尾节后加一个折叠块：

```markdown
<details>
<summary>🔍 本次 Adversarial Self-Review 自查结果（透明度记录）</summary>

- 日期完整性：✅ 全部 N 篇均在 age_cutoff 内 / ⚠️ 删除 M 篇超龄
- 事实-证据校对：✅ 无过度肯定 / ⚠️ 修订 K 处过度肯定
- 已有笔记一致性：✅ 所有 wikilink 验证通过 / ⚠️ 删除 J 个无效链接
- 再推论文标注：✅ 全部标注 / ⚠️ 补标 P 篇
- 自相矛盾扫描：✅ 无矛盾 / ⚠️ 修订 Q 处
- Claim-Evidence 三元组覆盖：✅ 覆盖 X / X 篇
</details>
```

如果**全部 ✅**，就照样写出来——这是给未来的你/用户的可追溯证据。
```

`new_string`:
```
### Phase 5.5: 强制自查（pipeline_guard.py）

**写完 Phase 5 内容 → 落到 /tmp/daily_papers_draft.md → 调 guard：**

```bash
python3 ../_shared/pipeline_guard.py \
    /tmp/daily_papers_draft.md \
    --enriched /tmp/daily_papers_enriched.json \
    --meta /tmp/daily_papers_search_meta.json \
    --notes "{NOTES_PATH}" \
    --json-out /tmp/guard_report.json
```

`{NOTES_PATH}` 是 Step 0 解析出来的 `论文笔记` 路径。

**exit code 处置：**
- `0` → guard 通过，跳过 Phase 5.6，直接进 Phase 6 保存
- `1` → guard 发现违规，进 Phase 5.6 自修订
- `2` → guard 内部错（输入文件缺失、JSON 解析失败等）→ 报 BLOCKED 告知用户，不要硬走

**guard 检的是三件硬事实：**

1. **C1 date_cutoff**：每篇推荐论文 `published_date ≥ age_cutoff`（从 enriched.json + meta.json 拉数据机械对照）
2. **C2 existing_note_wikilink**：每条 `📒 **已有笔记**: [[xxx]]` 行的 xxx 在 `{NOTES_PATH}` 下 glob 必须命中真实 .md 文件
3. **C3 critique_evidence_triples**：每个**非"已有笔记简化格式"**的论文段必须有 `🧪 锐评依据:` 块且 ≥2 条 `Claim/Evidence/Confidence`

**guard 不查的（继续靠你 LLM prose 自查，下面这两项相当于以前的 5.5.2 / 5.5.4）：**

#### 5.5.A 事实-证据校对（LLM 自查）

对每篇论文的「核心方法 / 对比方法 / 锐评 / 借鉴意义」做反向校验：

- **过度肯定检测**：搜出现「SOTA」「突破」「革命性」「最强」「首次」「全面超越」的句子。每一处都要回到 abstract / method_summary / method_names 里找具体数字或方法名支撑；找不到的，要么补「（摘要未给硬数字，待全文确认）」要么删
- **凭空硬伤检测**：搜锐评里说论文「缺 ablation」「没 baseline 对比」「没流式」这种话。回 enriched 数据的 `section_headers` 和 `captions` 检查——如果章节标题出现「Ablation Study」或表格标题出现「Comparison」，撤销指控
- **再推论文标注**：对 `is_re_recommend=true` 的论文，必须有「⏪ 再推提醒：这篇在 {last_recommend_date} 推荐过」一行

#### 5.5.B 自相矛盾扫描（LLM 自查）

- 同一篇的「借鉴意义」说「很有用」+ 锐评说「没价值」→ 选一个，删另一个
- 分流表里写「🔥 必读」+ 锐评结尾打 `💀` 或 `🤡` → 等级要么降为「👀 值得看」要么改 emoji
- 开头总评说「今天 TTS 在爆发」+ 实际只有 1 篇 TTS → 收口，改总评

LLM 自查发现的修改也写回 /tmp/daily_papers_draft.md；写回后再跑一次 guard 兜底（一般会过，guard 只会"宽松"加把锁）。

### Phase 5.6: 自修订（仅在 Phase 5.5 guard 失败时）

1. Read `/tmp/guard_report.json`
2. 按 `violations` 数组逐条修复 `/tmp/daily_papers_draft.md`：
   - **date_cutoff** → 从 draft 中删整段论文（含分流表对应行 + `### N. 标题` 详评段）+ 在「被排除的论文」节加一行「spec #3 guard: published {date} 早于 cutoff {cutoff}」
   - **existing_note_wikilink** → 仅删那条 `📒 **已有笔记**: [[xxx]]` 行，不删整段
   - **critique_evidence_triples** → 给指定论文段补 `Claim/Evidence/Confidence` triple 到 ≥ 2 条
3. 写回 `/tmp/daily_papers_draft.md`
4. 重跑同样的 `pipeline_guard.py` 命令
5. `exit 0` → 进 Phase 6
6. `exit 1`（第 2 轮仍违规）：
   ```bash
   cp /tmp/daily_papers_draft.md "/tmp/draft_blocked_$(date +%Y%m%d_%H%M%S).md"
   ```
   告诉用户：「BLOCKED：guard 第 2 轮仍 N 处违规（{summary.by_check}），draft 已落到 /tmp/draft_blocked_*.md。请人工修复后改名为 daily_papers_draft.md，再手动跑 Phase 6 或重跑本流水线」
   **不要 Write 到 vault**

#### 5.6.A 输出自查结果（嵌入 Phase 6 保存的日报末尾）

guard 通过后，把 `/tmp/guard_report.json` 的字段直接渲染成 details 块（数字来自 JSON，**不要凭记忆填**）：

```markdown
<details>
<summary>🔍 本次 Adversarial Self-Review 自查结果（pipeline_guard.py 自动生成）</summary>

| 检查 | 结果 |
|---|---|
| 5.5.1 日期完整性 (C1) | ✅ 全部 N 篇均在 age_cutoff 内 |
| 5.5.5 已有笔记 wikilink (C2) | ✅ 所有 X 个 wikilink 验证通过 |
| 5.5.3 🧪 锐评依据三元组 (C3) | ✅ Y / Y 篇满足 ≥2 triples |
| 5.5.A 事实-证据校对 | ⚙️ LLM 自查（guard 不强制） |
| 5.5.B 自相矛盾扫描 | ⚙️ LLM 自查（guard 不强制） |

guard report: 第 1 轮通过 / 第 2 轮通过（含 K 处自修订）
</details>
```

N = `summary.stats.papers_in_draft - summary.by_check.date_cutoff`
X = `summary.stats.wikilinks_checked`
Y = `summary.stats.papers_in_draft - summary.stats.papers_skipped_for_C3`
K = 第 2 轮才过时的自修订次数（仅在自修订发生时显示「含 K 处自修订」字段）
```

- [ ] **Step 3: Verify the edit landed and there's no orphaned text**

Run:
```bash
grep -nE "Phase 5\.(5|6)" /Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md
grep -c "pipeline_guard.py" /Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md
grep -c "5\.5\.1 日期完整性" /Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md
grep -c "对抗式自查" /Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md
```

Expected:
- First grep shows `Phase 5.5` (new title "强制自查") and `Phase 5.6` headings
- `pipeline_guard.py` count >= 2 (in invocation + COMPLETION mentions)
- "5.5.1 日期完整性" count == 1 (still appears once in the details template label)
- "对抗式自查" count >= 1 (in the details block summary)

If "5.5.1 日期完整性" count is 0, the details template label didn't land — re-edit. If it's >1, the old prose still has remnants — find and remove them.

- [ ] **Step 4: Commit the SKILL.md change**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git add skills/daily-papers-review/SKILL.md
cd /Users/xiangshu/DailyPaper && git commit -m "spec #3: review skill Phase 5.5 calls pipeline_guard.py + new Phase 5.6 self-revision

🤖 Generated with Claude Code"
echo "exit=$?"
```

Expected: exit=0.

---

## Task 10: End-to-end retrofit verification

Goal: prove that the 2026-05-19 retrofit-era draft (with OmniFlatten 2024-10, MiniCPM 2026-04, VibeVoice 2025-08) would be caught by the new guard, NOT silently saved.

**Files:** read-only verification

- [ ] **Step 1: Run guard against the retrofit fixture**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py \
    /Users/xiangshu/DailyPaper/scripts/fixtures/draft_retrofit_2026-05-19.md \
    --enriched /Users/xiangshu/DailyPaper/scripts/fixtures/enriched.json \
    --meta /Users/xiangshu/DailyPaper/scripts/fixtures/meta.json \
    --notes /Users/xiangshu/DailyPaper/scripts/fixtures/notes \
    --json-out /tmp/guard_retrofit.json
echo "exit=$?"
```

Expected: stderr `guard: 3 violations (date_cutoff=3, existing_note_wikilink=0, critique_evidence_triples=0) — see /tmp/guard_retrofit.json`; exit=1.

- [ ] **Step 2: Inspect the violations JSON**

Run:
```bash
python3 -c "
import json
r = json.load(open('/tmp/guard_retrofit.json'))
print('passed:', r['passed'])
print('total_violations:', r['summary']['total_violations'])
print('by_check:', r['summary']['by_check'])
print()
print('flagged papers:')
for v in r['violations']:
    if v['check'] == 'date_cutoff':
        print(f\"  {v['paper_arxiv_id']} ({v['paper_title']}): published {v['paper_published_date']} < cutoff {v['age_cutoff']}\")
"
```

Expected output:
```
passed: False
total_violations: 3
by_check: {'date_cutoff': 3, 'existing_note_wikilink': 0, 'critique_evidence_triples': 0}

flagged papers:
  2508.19205 (VibeVoice Old Hit): published 2025-08-15 < cutoff 2026-05-13
  2410.05000 (OmniFlatten Old): published 2024-10-10 < cutoff 2026-05-13
  2604.03000 (MiniCPM-o-4.5 Spring 2026): published 2026-04-15 < cutoff 2026-05-13
```

All 3 historical leakers must be flagged with correct arxiv IDs and dates. **This is the proof that spec #3 closes the 2026-05-19 retrofit hole.**

If any of the 3 is missing from the output, debug: check that the arxiv ID parse in guard matches the URL format in the fixture's `### N. Title` section.

---

## Task 11: Acceptance §7 checklist + spec #1 regression + COMPLETION

**Files:**
- Create: `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-pipeline-guard-COMPLETION.md`
- Final git commit

- [ ] **Step 1: Run all acceptance checks**

Run:
```bash
echo "=== Spec §7 Acceptance ==="
echo
echo "[1] guard exists + imports cleanly:"
python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('pg', '/Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('  ok; funcs:', [n for n in ('check_date_cutoff', 'check_existing_note_wikilinks', 'check_critique_triples', 'split_paper_sections', 'main') if hasattr(mod, n)])
"
echo
echo "[2] guard tests 7/7 PASS:"
python3 /Users/xiangshu/DailyPaper/scripts/test_pipeline_guard.py 2>&1 | tail -3
echo
echo "[3] review SKILL.md updated (no stale prose):"
echo -n "  对抗式自查 occurrences (allowed 1, in details block summary): "
grep -c "对抗式自查" /Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md
echo -n "  pipeline_guard.py mentions (must be >= 2): "
grep -c "pipeline_guard.py" /Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md
echo -n "  Phase 5.6 heading present: "
grep -c "### Phase 5.6" /Users/xiangshu/DailyPaper/skills/daily-papers-review/SKILL.md
echo
echo "[4] end-to-end retrofit catches 3 old papers (Task 10 redo):"
python3 /Users/xiangshu/DailyPaper/skills/_shared/pipeline_guard.py \
    /Users/xiangshu/DailyPaper/scripts/fixtures/draft_retrofit_2026-05-19.md \
    --enriched /Users/xiangshu/DailyPaper/scripts/fixtures/enriched.json \
    --meta /Users/xiangshu/DailyPaper/scripts/fixtures/meta.json \
    --notes /Users/xiangshu/DailyPaper/scripts/fixtures/notes \
    --json-out /tmp/guard_retrofit_final.json
RC=$?
echo "  exit code: $RC (expect 1)"
python3 -c "
import json
r = json.load(open('/tmp/guard_retrofit_final.json'))
print('  date_cutoff violations:', r['summary']['by_check']['date_cutoff'], '(expect 3)')
"
echo
echo "[5] spec #1 regression — test_fetch_no_trending.py 7/7:"
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py 2>&1 | tail -2
echo
echo "[6] git log shows spec #3 commits:"
cd /Users/xiangshu/DailyPaper && git log --oneline | head -5
echo
echo "[7] working tree clean:"
cd /Users/xiangshu/DailyPaper && git status --porcelain | wc -l
echo "  (expect 0)"
```

Read the output and verify each item against the expected value in parentheses. All must pass before writing COMPLETION.

- [ ] **Step 2: Write COMPLETION note**

Use Write tool to create `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-pipeline-guard-COMPLETION.md`:

```markdown
# Spec #3 Completion — 2026-05-20

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-pipeline-guard-design.md`
**Plan:** `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-pipeline-guard.md`

## What changed

- New `skills/_shared/pipeline_guard.py` (~220 lines, stdlib only) enforces 3 hard-fact checks:
  - C1 date_cutoff: every recommended paper published_date >= age_cutoff
  - C2 existing_note_wikilink: 📒 **已有笔记**: [[xxx]] must resolve to a real .md
  - C3 critique_evidence_triples: ≥2 Claim/Evidence/Confidence per non-existing-note paper
- New `scripts/test_pipeline_guard.py` (~250 lines, subprocess-driven, stdlib) — 7 tests
- New `scripts/fixtures/` (7 draft .md + enriched.json + meta.json + 2 stub notes)
- `skills/daily-papers-review/SKILL.md` Phase 5.5 prose replaced with `pipeline_guard.py` invocation; new Phase 5.6 (LLM self-revision on guard fail); Phase 5.5.5 self-review block now rendered from guard JSON, not LLM-written
- 2 git commits in `~/DailyPaper/`:
  - `spec #3: pipeline_guard.py + 7 unit tests + 7 fixtures`
  - `spec #3: review skill Phase 5.5 calls pipeline_guard.py + new Phase 5.6 self-revision`

## Acceptance §7 status

- [x] guard exists + imports cleanly
- [x] guard tests 7/7 PASS
- [x] review SKILL.md updated, no stale prose
- [x] end-to-end retrofit: all 3 historical leak papers (OmniFlatten 2024-10, VibeVoice 2025-08, MiniCPM 2026-04) caught by guard with exit 1 + 3 date_cutoff violations
- [x] spec #1 regression: test_fetch_no_trending.py still 7/7 PASS
- [x] git commits committed, working tree clean

## Notable observations

- TDD flow worked exactly as designed: 7/7 FAIL → skeleton brought 3 PASS → C1 brought 1 more → C2 brought 1 more → C3 brought last 2 = 7/7 PASS
- The retrofit fixture is preserved at `scripts/fixtures/draft_retrofit_2026-05-19.md` as a regression hedge — future spec changes that break date enforcement will be caught immediately
- LLM self-revision flow (Phase 5.6) was specified in prose only; the mechanical guard is the hard guarantee. Even if LLM ignores Phase 5.6 prompts, guard's exit code blocks Phase 6 save

## Pending follow-ups

- **spec #2** (PDF skill) — central pdftotext/pdfimages/pdftoppm/pdfplumber wrapper
- **spec #4** (Semantic Scholar / OpenAlex enrichment) — DOI cross-source; may extend C1 to support non-arxiv sources
- **end-to-end run with real LLM** — wait for arxiv 429 to clear, then trigger `今日论文推荐` once and confirm guard runs cleanly through review skill's new Phase 5.5/5.6
- **`skills/_backup/hf-trending-removed-2026-05-20.md`** can be deleted now (git history holds prior state); defer to a later micro-cleanup spec
```

- [ ] **Step 3: Stage and commit COMPLETION**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git add docs/superpowers/plans/2026-05-20-pipeline-guard-COMPLETION.md
cd /Users/xiangshu/DailyPaper && git commit -m "spec #3 completion record

All 7 acceptance items passed; 2026-05-19 retrofit hole closed:
guard exit=1 + 3 date_cutoff violations on retrofit fixture.

🤖 Generated with Claude Code"
echo "exit=$?"
git log --oneline | head -5
```

Expected: exit=0; log shows 3 spec #3 commits (guard+tests, SKILL.md, COMPLETION) on top of the 2 spec #0 commits.

---

## Notes for the engineer

1. **TDD discipline is the whole point.** Don't skip Task 3 → Task 4's "run tests, expect mixed PASS/FAIL" step. The progression FAIL→PASS at each check (C1, then C2, then C3) is what proves each check works in isolation. If you implement all 3 at once and run tests, you lose the per-check signal when something fails.

2. **No pytest.** All tests are stdlib `assert` + the `if __name__ == "__main__": main()` runner — same pattern as `scripts/test_fetch_no_trending.py`. Don't `pip install pytest`.

3. **subprocess.run is the correct invocation in tests.** Don't refactor tests to import guard as a module — the contract IS the CLI, and importing would bypass argparse + exit code handling. The few extra seconds of subprocess overhead are worth the contract clarity.

4. **The fixture enriched.json is shared across all tests.** It contains arxiv IDs for both passing and old papers. Each test's draft picks which IDs it references. Don't write a per-test enriched.json — the deduplication is intentional.

5. **`📒 **已有笔记**:` vs `📒 **笔记**:`** — these are different markers. C2 only checks `📒 **已有笔记**`. The `📒 **笔记**` marker is inserted by `daily-papers-notes` skill AFTER review (Phase 7), pointing to a not-yet-created file; guard correctly ignores it.

6. **The `🧪 锐评依据` regex uses backtick-wrapped Claim/Evidence/Confidence.** This is the existing convention (verified against the real 2026-05-20 daily report). Don't relax the regex to match unquoted forms — that would give false-positive triples from prose mentions of the words.

7. **`Path.rglob(f"{wikilink}.md")` handles Unicode filenames natively** on macOS. Don't normalize/escape.

8. **`set -e` is not used in Tasks 8/9/11 git commits** because git operations should report their own exit codes; bash's `echo "exit=$?"` makes them visible.

9. **`/tmp/daily_papers_draft.md` is a runtime convention.** The plan doesn't write to it during tests (tests use fixtures). It's only relevant when review skill is actually running in production.

10. **The SKILL.md edit in Task 9 is large.** If Edit fails on `old_string` not matching exactly, re-read the file and copy the actual current Phase 5.5 block character-for-character. The text might have minor whitespace differences from what's in this plan.
