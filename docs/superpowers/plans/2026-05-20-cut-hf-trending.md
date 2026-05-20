# Cut HF Trending from Daily Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove HF Trending source, its scoring boost, its age-exemption escape hatch, and its weekend re-recommend special case from the daily papers pipeline. After this change, the daily pipeline only consumes HF Daily + arXiv, and `published >= age_cutoff` is unconditionally enforced.

**Architecture:** Single-pass mechanical refactor across 4 files (1 JSON, 1 Python, 2 SKILL.md). Backup-first via a single Markdown archive at `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md` (B1 strategy, per spec §8) since `~/.claude/skills/` is not yet a git repo. Tests are static-grep + signature-import checks (no live network), with one live smoke run at the end.

**Tech Stack:**
- Python 3 (stdlib only — no pytest dependency)
- `grep`, `python3 -c`, plain `bash`
- Edit tool for precise string replacements
- No git operations (skills dir is not a git repo; spec #0 will fix this later)

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-cut-hf-trending-design.md`

---

## File Structure

**Files to CREATE:**
- `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md` — single Markdown archive containing all 5 deleted code blocks with file paths, line numbers, original code, removal reason, and notes for future "domain research" skill
- `/Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py` — Python unit test (stdlib only); 7 assertions covering signature, constants, config, and static grep on the 3 source files

**Files to MODIFY:**
- `~/.claude/skills/_shared/user-config.json` — remove `daily_papers.trending_age_exemption_upvotes` field (1 line + trailing-comma fix on prior line)
- `~/.claude/skills/daily-papers/fetch_and_score.py` — multiple edits (constant, score signature, hf-trending fetch block, age-exemption branch, weekend re-recommend branch, meta config, source_breakdown_of_final set)
- `~/.claude/skills/daily-papers-fetch/SKILL.md` — strip "HF trending" mentions (3 occurrences)
- `~/.claude/skills/daily-papers-review/SKILL.md` — strip "hf-trending" source format, Phase 5.5.1 `age_exempted` check, transparency template's exemption fields (5 occurrences)

**Files NOT to touch (per spec §3.2):**
- Historical daily reports under `/Users/xiangshu/DailyPaper/DailyPaper/DailyPapers/*.md`
- `.history.json`
- All other skill files (`review` skill's other phases, `notes`, `weekly`, `compare`, `highlights`, `library-import`, `generate-mocs`, `paper-reader`, `_shared/user_config.py`)

---

## Task 1: Sanity check pre-state

**Files:**
- Read-only verification

- [ ] **Step 1: Confirm spec exists and skill paths exist**

Run:
```bash
ls -la /Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-cut-hf-trending-design.md \
       ~/.claude/skills/_shared/user-config.json \
       ~/.claude/skills/daily-papers/fetch_and_score.py \
       ~/.claude/skills/daily-papers-fetch/SKILL.md \
       ~/.claude/skills/daily-papers-review/SKILL.md
```

Expected: all 5 files listed with non-zero size, no "No such file" errors.

- [ ] **Step 2: Record current `trending` occurrence counts**

Run:
```bash
grep -ic "trending" ~/.claude/skills/_shared/user-config.json
grep -ic "trending" ~/.claude/skills/daily-papers/fetch_and_score.py
grep -ic "trending" ~/.claude/skills/daily-papers-fetch/SKILL.md
grep -ic "trending" ~/.claude/skills/daily-papers-review/SKILL.md
```

Expected (per spec §3.1 — pre-state):
- `user-config.json`: 1
- `fetch_and_score.py`: 24
- `daily-papers-fetch/SKILL.md`: 3
- `daily-papers-review/SKILL.md`: 5

If counts differ materially (e.g., user added more references since spec audit), STOP and ask user. Otherwise proceed.

---

## Task 2: Create backup archive (B1)

**Files:**
- Create: `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md`

- [ ] **Step 1: Create backup directory**

Run:
```bash
mkdir -p ~/.claude/skills/_backup
```

Expected: command succeeds silently.

- [ ] **Step 2: Re-read the exact code blocks to be removed**

Run:
```bash
# Capture exact line ranges before any edit
sed -n '42,45p' ~/.claude/skills/daily-papers/fetch_and_score.py  # MAX_AGE_DAYS + TRENDING_AGE_EXEMPTION_UPVOTES constants
sed -n '58,105p' ~/.claude/skills/daily-papers/fetch_and_score.py # score_paper full body
sed -n '155,165p' ~/.claude/skills/daily-papers/fetch_and_score.py # _parse_hf_item is_trending call
sed -n '211,230p' ~/.claude/skills/daily-papers/fetch_and_score.py # fetch_hf_papers trending block
sed -n '361,365p' ~/.claude/skills/daily-papers/fetch_and_score.py # is_weekend init in merge
sed -n '395,420p' ~/.claude/skills/daily-papers/fetch_and_score.py # age-exemption branch + log + stats
sed -n '460,475p' ~/.claude/skills/daily-papers/fetch_and_score.py # weekend re-recommend
sed -n '545,565p' ~/.claude/skills/daily-papers/fetch_and_score.py # meta config + source_breakdown
grep -n "trending" ~/.claude/skills/daily-papers-fetch/SKILL.md
grep -n "trending" ~/.claude/skills/daily-papers-review/SKILL.md
```

Note: line numbers may have drifted slightly; trust grep output over the spec's "line ~N" hints. Record actual line numbers; you will paste these blocks into the backup file in the next step.

- [ ] **Step 3: Write the backup archive**

Use Write tool to create `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md` with this structure:

```markdown
# HF Trending Removal — Backup Archive

**Date:** 2026-05-20
**Spec:** /Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-cut-hf-trending-design.md
**Reason:** Repeated "old paper leak" incidents (2026-05-19 retrofit dropped OmniFlatten 2024-10, MiniCPM-o-4.5 2026-04, VibeVoice 2025-08). HF Trending's age-exemption was the leak vector. User has decided to split daily vs domain-research into two pipelines; this code belongs to the future "domain research" skill, not daily.

This file preserves the deleted code so a future `daily-papers-domain-research` skill can re-use the fetch + scoring logic. Once spec #0 (repo restructure) is done and `~/.claude/skills/` is under git, this archive can be removed in favor of `git show <commit>`.

---

## 1. user-config.json — trending exemption field

**File:** `~/.claude/skills/_shared/user-config.json`
**Removed line:**
```json
    "trending_age_exemption_upvotes": 200
```
(plus the trailing comma on the preceding `"max_age_days": 7` line)

---

## 2. fetch_and_score.py — TRENDING_AGE_EXEMPTION_UPVOTES constant

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (~lines 44-45 pre-edit)
**Removed:**
```python
# 例外：HF Trending 的爆款（upvotes >= 此阈值）即使超龄也保留，避免漏真 SOTA。设为 None 关闭例外
TRENDING_AGE_EXEMPTION_UPVOTES = _CONFIG.get("trending_age_exemption_upvotes", 200)
```

---

## 3. fetch_and_score.py — score_paper trending boost branch

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (~lines 58-105 pre-edit)
**Removed parts of `score_paper`:**
- function signature parameter `is_trending: bool = False`
- `keyword_hits` counter (was only used inside trending branch)
- trending boost branch (entire section "# 4. Trending boost (HF sources only)")

[paste exact original code captured in Step 2 here]

---

## 4. fetch_and_score.py — _parse_hf_item trending dispatch

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (~lines 157-158 pre-edit)
**Removed:**
```python
is_trending = source == "hf-trending"
paper["score"] = score_paper(paper, is_trending=is_trending)
```
**Replaced with:**
```python
paper["score"] = score_paper(paper)
```

---

## 5. fetch_and_score.py — fetch_hf_papers hf-trending block

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (~lines 211-226 pre-edit)
**Removed (full block, from comment "# ── hf-trending: always single call (not date-dependent) ──" through the items loop):**

[paste exact original code captured in Step 2 here]

Reuse notes for future domain-research skill:
- Endpoint: `{HF_BASE}/api/daily_papers?sort=trending&limit=50`
- Score boost tiered by upvotes (10/5/2 thresholds, +3/+2/+1 score)
- Relevance gate: only boost if keyword_hits + domain_hits > 0

---

## 6. fetch_and_score.py — age-exemption branch in merge_and_dedup

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (~lines 397-407 pre-edit, plus `aged_exempted = 0` initializer ~line 371, log message ~line 411-414, stats key ~line 418)
**Removed:**

[paste exact original code captured in Step 2 here]

---

## 7. fetch_and_score.py — weekend re-recommend trending branch

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (~lines 463-470 pre-edit)
**Removed:**

[paste exact original code captured in Step 2 here]

Also removed `is_weekend` initializer on line ~361 (became unused after this deletion).

---

## 8. fetch_and_score.py — meta config & source_breakdown_of_final

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (~lines 549-561 pre-edit)
**Removed:**
- `"trending_age_exemption_upvotes": TRENDING_AGE_EXEMPTION_UPVOTES` from meta.config
- `"hf-trending"` from `source_breakdown_of_final` set comprehension
- `"age_exempted_in_final": sum(...)` key entirely

---

## 9. daily-papers-fetch/SKILL.md — trending mentions

[paste exact original lines from Step 2 grep here]

---

## 10. daily-papers-review/SKILL.md — trending source format + age_exempted check + transparency template

[paste exact original lines from Step 2 grep here]
```

Replace each `[paste exact original code captured in Step 2 here]` with the actual code blocks from Step 2's `sed` output. The bracket placeholders MUST be replaced — do not leave them as-is.

- [ ] **Step 4: Verify backup archive is complete**

Run:
```bash
wc -l ~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md
grep -c "paste exact original" ~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md
```

Expected:
- Line count > 150 (substantial archive)
- `paste exact original` count == 0 (all placeholders replaced)

If either fails, fix the archive before proceeding.

---

## Task 3: Write failing unit tests

**Files:**
- Create: `/Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py`

- [ ] **Step 1: Create the test file**

Use Write tool to create `/Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py`:

```python
#!/usr/bin/env python3
"""Static tests verifying HF Trending has been removed from daily pipeline.

Run:
    python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py

Exits 0 if all assertions pass, 1 otherwise. Each test prints PASS/FAIL.
Tests are pure static analysis + import-time checks — no network, no
side effects on vault.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

SKILLS = Path.home() / ".claude" / "skills"
FETCH_PY = SKILLS / "daily-papers" / "fetch_and_score.py"
USER_CFG = SKILLS / "_shared" / "user-config.json"
FETCH_SKILL = SKILLS / "daily-papers-fetch" / "SKILL.md"
REVIEW_SKILL = SKILLS / "daily-papers-review" / "SKILL.md"


def _import_fetch_module():
    """Import fetch_and_score.py as a module without executing main()."""
    spec = importlib.util.spec_from_file_location("fetch_and_score", FETCH_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_score_paper_no_is_trending_kwarg():
    """score_paper must NOT accept an is_trending keyword argument."""
    mod = _import_fetch_module()
    paper = {"title": "test", "abstract": "test"}
    try:
        mod.score_paper(paper, is_trending=True)
    except TypeError:
        return
    raise AssertionError("score_paper still accepts is_trending kwarg")


def test_no_trending_exemption_constant():
    """Module must not define TRENDING_AGE_EXEMPTION_UPVOTES."""
    mod = _import_fetch_module()
    assert not hasattr(mod, "TRENDING_AGE_EXEMPTION_UPVOTES"), (
        "TRENDING_AGE_EXEMPTION_UPVOTES still defined in fetch_and_score.py"
    )


def test_user_config_no_trending_field():
    """user-config.json must not contain trending_age_exemption_upvotes."""
    cfg = json.loads(USER_CFG.read_text())
    daily = cfg.get("daily_papers", {})
    assert "trending_age_exemption_upvotes" not in daily, (
        "trending_age_exemption_upvotes still present in user-config.json"
    )


def test_fetch_py_no_trending_string():
    """fetch_and_score.py code (excluding comments) must not contain 'trending'."""
    text = FETCH_PY.read_text()
    code_lines = [
        ln for ln in text.splitlines()
        if not ln.lstrip().startswith("#") and not ln.lstrip().startswith('"""')
    ]
    code_text = "\n".join(code_lines)
    matches = re.findall(r"(?i)trending", code_text)
    assert not matches, (
        f"fetch_and_score.py code still contains {len(matches)} 'trending' "
        f"refs (case-insensitive)"
    )


def test_fetch_skill_no_trending_string():
    """daily-papers-fetch/SKILL.md must not contain 'trending'."""
    text = FETCH_SKILL.read_text()
    matches = re.findall(r"(?i)trending", text)
    assert not matches, (
        f"daily-papers-fetch/SKILL.md still contains {len(matches)} 'trending' refs"
    )


def test_review_skill_no_trending_string():
    """daily-papers-review/SKILL.md must not contain 'trending'."""
    text = REVIEW_SKILL.read_text()
    matches = re.findall(r"(?i)trending", text)
    assert not matches, (
        f"daily-papers-review/SKILL.md still contains {len(matches)} 'trending' refs"
    )


def test_review_skill_no_age_exempted_string():
    """daily-papers-review/SKILL.md must not reference age_exempted."""
    text = REVIEW_SKILL.read_text()
    matches = re.findall(r"age_exempted", text)
    assert not matches, (
        f"daily-papers-review/SKILL.md still contains {len(matches)} 'age_exempted' refs"
    )


TESTS = [
    test_score_paper_no_is_trending_kwarg,
    test_no_trending_exemption_constant,
    test_user_config_no_trending_field,
    test_fetch_py_no_trending_string,
    test_fetch_skill_no_trending_string,
    test_review_skill_no_trending_string,
    test_review_skill_no_age_exempted_string,
]


def main():
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

- [ ] **Step 2: Run tests to verify they FAIL against current trending-containing code**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py
```

Expected: exit code 1, with output like:
```
FAIL: test_score_paper_no_is_trending_kwarg: score_paper still accepts is_trending kwarg
FAIL: test_no_trending_exemption_constant: TRENDING_AGE_EXEMPTION_UPVOTES still defined ...
FAIL: test_user_config_no_trending_field: trending_age_exemption_upvotes still present ...
FAIL: test_fetch_py_no_trending_string: fetch_and_score.py code still contains N 'trending' refs ...
FAIL: test_fetch_skill_no_trending_string: ...
FAIL: test_review_skill_no_trending_string: ...
FAIL: test_review_skill_no_age_exempted_string: ...
0 / 7 passed
```

All 7 should fail. If any pass before the edits, the test is wrong — fix it before proceeding.

---

## Task 4: Edit `_shared/user-config.json`

**Files:**
- Modify: `~/.claude/skills/_shared/user-config.json`

- [ ] **Step 1: Apply edit**

Use Edit tool:
- `file_path`: `~/.claude/skills/_shared/user-config.json` (resolve `~` to absolute path)
- `old_string`:
  ```
      "max_age_days": 7,
      "trending_age_exemption_upvotes": 200
    },
  ```
- `new_string`:
  ```
      "max_age_days": 7
    },
  ```

- [ ] **Step 2: Verify**

Run:
```bash
python3 -c "import json; cfg=json.load(open('/Users/xiangshu/.claude/skills/_shared/user-config.json')); assert 'trending_age_exemption_upvotes' not in cfg['daily_papers'], 'still present'; print('OK')"
grep -ic "trending" ~/.claude/skills/_shared/user-config.json
```

Expected: `OK` printed, grep returns `0`.

---

## Task 5: Edit `daily-papers/fetch_and_score.py`

**Files:**
- Modify: `~/.claude/skills/daily-papers/fetch_and_score.py`

Each step below is a separate Edit. Apply them in order. After all edits, the file should have **zero** `trending` matches outside comments that intentionally reference "removed in spec #1".

- [ ] **Step 1: Remove TRENDING_AGE_EXEMPTION_UPVOTES constant**

Edit:
- `old_string`:
  ```
  # 论文 published date 距离今天最大允许天数；超龄一律剔除（HF Trending 把老 hot paper 顶上来的根治办法）
  MAX_AGE_DAYS = _CONFIG.get("max_age_days", 7)
  # 例外：HF Trending 的爆款（upvotes >= 此阈值）即使超龄也保留，避免漏真 SOTA。设为 None 关闭例外
  TRENDING_AGE_EXEMPTION_UPVOTES = _CONFIG.get("trending_age_exemption_upvotes", 200)
  ```
- `new_string`:
  ```
  # 论文 published date 距今最大允许天数；超龄一律剔除
  MAX_AGE_DAYS = _CONFIG.get("max_age_days", 7)
  ```

- [ ] **Step 2: Simplify score_paper signature and remove trending boost branch**

Edit:
- `old_string`:
  ```
  def score_paper(paper: dict, is_trending: bool = False) -> int:
      text = (paper["title"] + " " + paper["abstract"]).lower()
      title_lower = paper["title"].lower()

      # 1. Negative keywords → instant reject
      for neg in NEGATIVE_KEYWORDS:
          if neg in text:
              return -999

      score = 0

      # 2. Positive keywords
      keyword_hits = 0
      for kw in KEYWORDS:
          if kw in title_lower:
              score += 3
              keyword_hits += 1
          elif kw in text:
              score += 1
              keyword_hits += 1

      # 3. Domain boost
      domain_hits = sum(1 for kw in DOMAIN_BOOST_KEYWORDS if kw in text)
      if domain_hits >= 2:
          score += 2
      elif domain_hits == 1:
          score += 1

      # 4. Trending boost (HF sources only)
      #    GATE: only apply if paper has at least 1 keyword or domain match,
      #    to prevent irrelevant but popular papers from flooding the list
      has_relevance = keyword_hits > 0 or domain_hits > 0
      if is_trending:
          upvotes = paper.get("hf_upvotes", 0) or 0
          if has_relevance:
              # Relevant + trending → full boost
              if upvotes >= 10:
                  score += 3
              elif upvotes >= 5:
                  score += 2
              elif upvotes >= 2:
                  score += 1
          else:
              # No relevance → minimal boost (only very popular papers get a chance)
              if upvotes >= 20:
                  score += 1

      return score
  ```
- `new_string`:
  ```
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

      return score
  ```

- [ ] **Step 3: Simplify _parse_hf_item — remove is_trending dispatch**

Edit:
- `old_string`:
  ```
      is_trending = source == "hf-trending"
      paper["score"] = score_paper(paper, is_trending=is_trending)
  ```
- `new_string`:
  ```
      paper["score"] = score_paper(paper)
  ```

- [ ] **Step 4: Remove hf-trending fetch block from fetch_hf_papers**

Edit:
- `old_string`:
  ```
      # ── hf-trending: always single call (not date-dependent) ──
      endpoint = f"{_HF_BASE}/api/daily_papers?sort=trending&limit=50"
      print(f"  Fetching hf-trending...", file=sys.stderr)
      raw = fetch_url(endpoint)
      if raw:
          try:
              items = json.loads(raw)
          except json.JSONDecodeError:
              items = []
              print(f"  [WARN] bad JSON from hf-trending", file=sys.stderr)
          for item in items:
              result = _parse_hf_item(item, "hf-trending")
              if result:
                  arxiv_id, paper = result
                  if arxiv_id not in papers or paper["score"] > papers[arxiv_id]["score"]:
                      papers[arxiv_id] = paper

      result = list(papers.values())
      print(f"  HF: {len(result)} papers after scoring", file=sys.stderr)
      return result
  ```
- `new_string`:
  ```
      result = list(papers.values())
      print(f"  HF: {len(result)} papers after scoring", file=sys.stderr)
      return result
  ```

- [ ] **Step 5: Remove age-exemption branch + counter init + log + stats key**

Edit:
- `old_string`:
  ```
      age_window = MAX_AGE_DAYS + (days - 1)
      age_cutoff = target_date - timedelta(days=age_window)
      aged_out = 0
      aged_exempted = 0
      age_filtered: list[dict] = []
  ```
- `new_string`:
  ```
      age_window = MAX_AGE_DAYS + (days - 1)
      age_cutoff = target_date - timedelta(days=age_window)
      aged_out = 0
      age_filtered: list[dict] = []
  ```

Then a second Edit:
- `old_string`:
  ```
          if pub_date >= age_cutoff:
              age_filtered.append(p)
              continue
          # 超龄。例外：HF Trending 爆款（upvotes 极高）保留
          upvotes = p.get("hf_upvotes") or 0
          if (
              TRENDING_AGE_EXEMPTION_UPVOTES is not None
              and p.get("source") == "hf-trending"
              and upvotes >= TRENDING_AGE_EXEMPTION_UPVOTES
          ):
              p["age_exempted"] = True  # 让后续 review 阶段可显式标注
              age_filtered.append(p)
              aged_exempted += 1
              continue
          aged_out += 1
      print(
          f"  Age filter (cutoff={age_cutoff}, window={age_window}d): "
          f"kept {len(age_filtered)} / dropped {aged_out}"
          + (f" / exempted {aged_exempted} HF爆款" if aged_exempted else ""),
          file=sys.stderr,
      )
      stats["filter_steps"]["age_filter"] = {
          "kept": len(age_filtered),
          "dropped_aged": aged_out,
          "exempted_hf_trending": aged_exempted,
      }
  ```
- `new_string`:
  ```
          if pub_date >= age_cutoff:
              age_filtered.append(p)
              continue
          aged_out += 1
      print(
          f"  Age filter (cutoff={age_cutoff}, window={age_window}d): "
          f"kept {len(age_filtered)} / dropped {aged_out}",
          file=sys.stderr,
      )
      stats["filter_steps"]["age_filter"] = {
          "kept": len(age_filtered),
          "dropped_aged": aged_out,
      }
  ```

- [ ] **Step 6: Remove weekend re-recommend trending special case**

Edit:
- `old_string`:
  ```
      # ── cross-day dedup ──
      deduped: dict[str, dict] = {}
      removed = 0
      for aid, p in by_id.items():
          if aid in history_ids:
              # Weekend: keep trending with upvotes >= 5
              if is_weekend and p.get("source") == "hf-trending" and (p.get("hf_upvotes") or 0) >= 5:
                  p["is_re_recommend"] = True
                  p["last_recommend_date"] = history_ids[aid]
                  deduped[aid] = p
              else:
                  removed += 1
          else:
              deduped[aid] = p
  ```
- `new_string`:
  ```
      # ── cross-day dedup ──
      deduped: dict[str, dict] = {}
      removed = 0
      for aid, p in by_id.items():
          if aid in history_ids:
              removed += 1
          else:
              deduped[aid] = p
  ```

- [ ] **Step 7: Remove now-unused `is_weekend` initializer in merge_and_dedup**

Note: The `is_weekend = target_date.weekday() >= 5` line on the FIRST line of `merge_and_dedup`'s body is now unused. The same line in `main()` (which logs `"(weekend)"`) MUST stay — different scope.

Edit:
- `old_string`:
  ```
  def merge_and_dedup(
      hf_papers: list[dict],
      arxiv_papers: list[dict],
      target_date,
      days: int = 1,
      top_n: int = TOP_N,
  ) -> list[dict]:
      is_weekend = target_date.weekday() >= 5

      # ── age filter: drop papers older than today - (days_window + MAX_AGE_DAYS) ──
  ```
- `new_string`:
  ```
  def merge_and_dedup(
      hf_papers: list[dict],
      arxiv_papers: list[dict],
      target_date,
      days: int = 1,
      top_n: int = TOP_N,
  ) -> list[dict]:
      # ── age filter: drop papers older than today - (days_window + MAX_AGE_DAYS) ──
  ```

- [ ] **Step 8: Clean meta config dict and source_breakdown_of_final set**

Edit:
- `old_string`:
  ```
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
              "trending_age_exemption_upvotes": TRENDING_AGE_EXEMPTION_UPVOTES,
          },
          "source_breakdown_of_final": {
              s: sum(1 for p in top if p.get("source") == s)
              for s in {"hf-daily", "hf-trending", "arxiv"}
          },
          "age_exempted_in_final": sum(1 for p in top if p.get("age_exempted")),
      }
  ```
- `new_string`:
  ```
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
      }
  ```

- [ ] **Step 9: Verify all `trending` references in fetch_and_score.py are gone**

Run:
```bash
grep -in "trending" ~/.claude/skills/daily-papers/fetch_and_score.py
```

Expected: **no output** (no matches anywhere — including comments). If any match remains, identify it and decide whether it's a legitimate explanatory comment (rare — prefer to delete) or a missed code reference (must fix).

- [ ] **Step 10: Verify file still parses as Python**

Run:
```bash
python3 -c "import ast; ast.parse(open('/Users/xiangshu/.claude/skills/daily-papers/fetch_and_score.py').read()); print('OK')"
```

Expected: `OK`. If SyntaxError, find the line and fix indentation / orphaned syntax.

- [ ] **Step 11: Verify module still imports without runtime error**

Run:
```bash
python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('fas', '/Users/xiangshu/.claude/skills/daily-papers/fetch_and_score.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('OK; score_paper sig:', mod.score_paper.__code__.co_varnames[:mod.score_paper.__code__.co_argcount])
print('TRENDING_AGE_EXEMPTION_UPVOTES exists:', hasattr(mod, 'TRENDING_AGE_EXEMPTION_UPVOTES'))
"
```

Expected:
```
OK; score_paper sig: ('paper',)
TRENDING_AGE_EXEMPTION_UPVOTES exists: False
```

---

## Task 6: Edit `daily-papers-fetch/SKILL.md`

**Files:**
- Modify: `~/.claude/skills/daily-papers-fetch/SKILL.md`

- [ ] **Step 1: Locate current trending references**

Run:
```bash
grep -in "trending" ~/.claude/skills/daily-papers-fetch/SKILL.md
```

Expected: 3 matches with line numbers. Record them.

- [ ] **Step 2: Read the file around each match for exact context**

Use Read tool on `~/.claude/skills/daily-papers-fetch/SKILL.md` with no offset — read the full file (it's small).

- [ ] **Step 3: Edit each trending reference**

For each grep hit, choose the appropriate strategy:
- **Phase 1+2 description** ("并行抓取 HuggingFace Daily + Trending API 和 arXiv API"): Edit to remove "+ Trending" so it reads "并行抓取 HuggingFace Daily API 和 arXiv API"
- **Weekend strategy bullet** ("周末策略：arXiv 周末不更新，HF daily 周末基本为空，但 HF trending 持续更新。周末主要依赖 trending 来源"): Replace with: "**周末策略**：HF Daily 周末通常为空，arXiv 周末 cs.SD/eess.AS 也罕有发表，日报可能很瘦或为空。这是正常的，不做特殊回退。"
- **Any other mention** (e.g., the "hf-trending" line in the source_counts section description): delete the mention so the prose reflects only HF Daily + arXiv

Use one Edit per occurrence with sufficient surrounding context to make `old_string` unique. If two occurrences share identical surrounding text, use `replace_all: true`.

- [ ] **Step 4: Verify zero trending references remain**

Run:
```bash
grep -ic "trending" ~/.claude/skills/daily-papers-fetch/SKILL.md
```

Expected: `0`.

- [ ] **Step 5: Verify SKILL.md is still readable as a single document**

Run:
```bash
head -1 ~/.claude/skills/daily-papers-fetch/SKILL.md
wc -l ~/.claude/skills/daily-papers-fetch/SKILL.md
```

Expected: First line is `---` (YAML frontmatter start); line count > 100. Eyeball that the file still has clear structure.

---

## Task 7: Edit `daily-papers-review/SKILL.md`

**Files:**
- Modify: `~/.claude/skills/daily-papers-review/SKILL.md`

- [ ] **Step 1: Locate current references**

Run:
```bash
grep -in "trending\|age_exempted\|exempted\|豁免" ~/.claude/skills/daily-papers-review/SKILL.md
```

Expected: multiple matches across source format mapping (~line 92-95), Phase 5.5.1 (~line 236-237), and transparency template (~line 313-321). Record all line numbers.

- [ ] **Step 2: Read the file around each match**

Use Read tool on `~/.claude/skills/daily-papers-review/SKILL.md` with sufficient `offset` and `limit` to see the source-format section, Phase 5.5.1, and transparency template.

- [ ] **Step 3: Edit source format mapping**

Edit:
- `old_string` (the mapping under "来源格式规则"):
  ```
  **来源格式规则**（按 source 字段分别显示）：
  - `hf-daily` → `📰 HF Daily，⬆️ {hf_upvotes}`
  - `hf-trending` → 🔥 HF Trending，⬆️ {hf_upvotes}`
  - `arxiv` → `📄 arXiv 关键词检索`（不显示 upvotes，因为没有）
  ```
- `new_string`:
  ```
  **来源格式规则**（按 source 字段分别显示）：
  - `hf-daily` → `📰 HF Daily，⬆️ {hf_upvotes}`
  - `arxiv` → `📄 arXiv 关键词检索`（不显示 upvotes，因为没有）
  ```

- [ ] **Step 4: Edit Phase 5.5.1 — remove age_exempted check**

Edit:
- `old_string`:
  ```
  - 任何一篇 `date < age_cutoff` 且**没有** `age_exempted: true` 标记 → **立刻从推荐表删掉**，理由写到「被排除的论文」节
  - 命中 `age_exempted: true` 的论文，必须在锐评里**显式说明**「这是被超龄豁免进来的 HF 爆款（upvotes={n}），不是本周新论文」
  ```
- `new_string`:
  ```
  - 任何一篇 `date < age_cutoff` → **立刻从推荐表删掉**，理由写到「被排除的论文」节
  ```

- [ ] **Step 5: Audit any remaining "exempted" / "豁免" mentions in self-review template**

Run:
```bash
grep -n "exempted\|豁免" ~/.claude/skills/daily-papers-review/SKILL.md
```

The "🔍 本次 Adversarial Self-Review 自查结果" folding block label `- 日期完整性：✅ 全部 N 篇均在 age_cutoff 内 / ⚠️ 删除 M 篇超龄` should be **kept as-is** — "超龄" here means "older than cutoff", not "exemption granted", so it stays correct after the exemption is removed.

But if grep returns lines containing the **word** "exempted" or "豁免" (e.g., "豁免 N 篇 HF 爆款" elsewhere in this SKILL.md), edit each occurrence to delete the exemption clause. Use one Edit per occurrence; `old_string` should be the full sentence/bullet containing the word.

Expected after edits: `grep -c "exempted\|豁免" ~/.claude/skills/daily-papers-review/SKILL.md` returns `0`.

- [ ] **Step 6: Edit transparency template**

Edit:
- `old_string`:
  ```
  - **时间窗口**：published date ≥ {age_cutoff}（即最近 {age_window_days} 天）
  - **arXiv 类目**：{cs.SD, eess.AS, cs.CL, cs.MM, cs.HC}
  - **关键词数**：{keywords_count} 正向 / {negative_keywords_count} 负向 / {domain_boost_count} 加分
  - **打分门槛**：min_score = {min_score}
  - **HF 超龄豁免阈值**：upvotes ≥ {trending_age_exemption_upvotes}
  - **数据流**：HF {hf} 篇 + arXiv {arxiv} 篇 → 年龄过滤剩 {age_kept}（丢 {age_dropped}，豁免 {exempted}） → 去重 {merged_unique} → 历史去重 {history_kept}（去掉 {history_removed} 已推） → min_score 过 {score_kept} → 历史回补 {backfill} → **最终 {final_count}**
  - **最终入选来源**：HF Daily {n} + HF Trending {n} + arXiv {n}{；含超龄豁免 N 篇 if > 0}
  ```
- `new_string`:
  ```
  - **时间窗口**：published date ≥ {age_cutoff}（即最近 {age_window_days} 天）
  - **arXiv 类目**：{cs.SD, eess.AS, cs.CL, cs.MM, cs.HC}
  - **关键词数**：{keywords_count} 正向 / {negative_keywords_count} 负向 / {domain_boost_count} 加分
  - **打分门槛**：min_score = {min_score}
  - **数据流**：HF {hf} 篇 + arXiv {arxiv} 篇 → 年龄过滤剩 {age_kept}（丢 {age_dropped}） → 去重 {merged_unique} → 历史去重 {history_kept}（去掉 {history_removed} 已推） → min_score 过 {score_kept} → 历史回补 {backfill} → **最终 {final_count}**
  - **最终入选来源**：HF Daily {n} + arXiv {n}
  ```

- [ ] **Step 7: Verify zero trending / age_exempted references remain**

Run:
```bash
grep -ic "trending" ~/.claude/skills/daily-papers-review/SKILL.md
grep -c "age_exempted" ~/.claude/skills/daily-papers-review/SKILL.md
grep -c "trending_age_exemption_upvotes" ~/.claude/skills/daily-papers-review/SKILL.md
grep -c "超龄豁免" ~/.claude/skills/daily-papers-review/SKILL.md
```

Expected: all four return `0`. If the "豁免" word remains anywhere (e.g., in unrelated prose), evaluate case-by-case.

- [ ] **Step 8: Verify SKILL.md still has clean structure**

Run:
```bash
head -1 ~/.claude/skills/daily-papers-review/SKILL.md
wc -l ~/.claude/skills/daily-papers-review/SKILL.md
```

Expected: first line `---`, line count still > 300 (we deleted ~6 lines from a 365-line file).

---

## Task 8: Run unit tests — expect ALL PASS

**Files:**
- Run: `/Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py`

- [ ] **Step 1: Run all tests**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py
```

Expected:
```
PASS: test_score_paper_no_is_trending_kwarg
PASS: test_no_trending_exemption_constant
PASS: test_user_config_no_trending_field
PASS: test_fetch_py_no_trending_string
PASS: test_fetch_skill_no_trending_string
PASS: test_review_skill_no_trending_string
PASS: test_review_skill_no_age_exempted_string

7 / 7 passed
```

Exit code: 0.

If any test FAILs, return to the relevant Task (Task 4-7) and fix the missed reference. Do NOT proceed to Task 9 with failing tests.

---

## Task 9: Live integration smoke test

**Files:**
- No edits — runtime verification only

⚠️ This step requires live network to HF + arXiv. Skip if offline; defer this Task to next online opportunity.

- [ ] **Step 1: Run fetch with current date**

Run:
```bash
python3 ~/.claude/skills/daily-papers/fetch_and_score.py \
    > /tmp/daily_papers_top30.json \
    2> /tmp/fetch_stderr.log
echo "exit=$?"
```

Expected: `exit=0`. Stderr log shows fetching steps.

- [ ] **Step 2: Confirm stderr never mentions hf-trending**

Run:
```bash
grep -c "trending" /tmp/fetch_stderr.log
```

Expected: `0`. If non-zero, a deletion was missed.

- [ ] **Step 3: Confirm output JSON contains no hf-trending source**

Run:
```bash
python3 -c "
import json
data = json.load(open('/tmp/daily_papers_top30.json'))
sources = set(p.get('source', '') for p in data)
print('count:', len(data))
print('sources:', sources)
assert 'hf-trending' not in sources, f'hf-trending leaked: {sources}'
print('OK')
"
```

Expected output ends with `OK`. `sources` should be a subset of `{'arxiv', 'hf-daily'}`.

- [ ] **Step 4: Confirm no paper carries `age_exempted` field**

Run:
```bash
python3 -c "
import json
data = json.load(open('/tmp/daily_papers_top30.json'))
exempted = [p for p in data if 'age_exempted' in p]
assert not exempted, f'age_exempted survivors: {len(exempted)}'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 5: Confirm meta file matches new schema**

Run:
```bash
python3 -c "
import json
meta = json.load(open('/tmp/daily_papers_search_meta.json'))
assert 'trending_age_exemption_upvotes' not in meta.get('config', {}), 'trending key in config'
assert 'age_exempted_in_final' not in meta, 'age_exempted_in_final still present'
assert 'exempted_hf_trending' not in meta.get('filter_steps', {}).get('age_filter', {}), 'exempted_hf_trending still in filter_steps'
sb = meta.get('source_breakdown_of_final', {})
assert set(sb.keys()) <= {'hf-daily', 'arxiv'}, f'breakdown keys: {set(sb.keys())}'
print('OK; final_count =', meta.get('final_count'))
"
```

Expected: `OK; final_count = N` with N a non-negative integer.

- [ ] **Step 6: Sanity check — every paper passes age cutoff**

Run:
```bash
python3 -c "
import json
from datetime import datetime
data = json.load(open('/tmp/daily_papers_top30.json'))
meta = json.load(open('/tmp/daily_papers_search_meta.json'))
cutoff = datetime.strptime(meta['age_cutoff'], '%Y-%m-%d').date()
violators = []
for p in data:
    pub_str = (p.get('date') or '')[:10]
    if not pub_str:
        continue
    try:
        pub = datetime.strptime(pub_str, '%Y-%m-%d').date()
        if pub < cutoff:
            violators.append((p.get('title', '')[:60], pub_str))
    except ValueError:
        continue
print(f'cutoff={cutoff}, papers={len(data)}, violators={len(violators)}')
for t, d in violators:
    print(f'  VIOLATION: {d} | {t}')
assert not violators, 'papers older than age_cutoff present'
print('OK')
"
```

Expected: `OK`. **This is the core proof that the leak is fixed.**

---

## Task 10: Weekly digest regression (spec §6.3)

**Files:**
- No edits — verification only that weekly digest still parses past daily reports

⚠️ Requires the local Obsidian vault to have at least one past daily report (e.g., `/Users/xiangshu/DailyPaper/DailyPaper/DailyPapers/2026-05-19-论文推荐.md`). If no past reports exist, skip this Task.

- [ ] **Step 1: Identify past daily reports**

Run:
```bash
ls /Users/xiangshu/DailyPaper/DailyPaper/DailyPapers/*-论文推荐.md 2>/dev/null
```

Expected: at least one `.md` file path. If none, skip Task 10 and note in completion file.

- [ ] **Step 2: Confirm past reports still parse as valid Markdown + frontmatter**

Run:
```bash
python3 -c "
import re, pathlib
reports = sorted(pathlib.Path('/Users/xiangshu/DailyPaper/DailyPaper/DailyPapers/').glob('*-论文推荐.md'))
print(f'reports: {len(reports)}')
for r in reports:
    text = r.read_text()
    has_fm = text.startswith('---\n')
    has_close = '\n---\n' in text[3:200]
    paper_count = len(re.findall(r'^### \d+\.', text, re.MULTILINE))
    has_trending_word = 'hf-trending' in text or 'HF Trending' in text or '🔥 HF Trending' in text
    print(f'  {r.name}: frontmatter={has_fm and has_close} | papers={paper_count} | mentions_trending={has_trending_word}')
"
```

Expected: each row prints, no exception. `mentions_trending=True` is **expected** for historical reports (they were generated before this spec); we are NOT rewriting history. The goal is just to confirm the files are still well-formed.

- [ ] **Step 3: Confirm review SKILL.md's prose still describes a coherent flow**

Re-read `~/.claude/skills/daily-papers-review/SKILL.md` end-to-end (use Read tool, no offset/limit). Eyeball:
- Phase 4 (笔记库索引) still references HF Daily + arXiv only
- Phase 5 (毒舌点评) source format mapping shows only 2 sources
- Phase 5.5.1 doesn't mention `age_exempted`
- Phase 6 transparency template's "数据流" arrow reads cleanly

If you find any dangling fragment (broken bullet, stray comma, half-deleted sentence), fix with a follow-up Edit.

---

## Task 11: Acceptance checklist + completion note

**Files:**
- Create: `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-cut-hf-trending-COMPLETION.md`

- [ ] **Step 1: Walk the spec's acceptance criteria (§9)**

Run all checks at once:
```bash
echo "=== Acceptance §9 ==="
echo "[1] fetch_and_score.py no 'trending' (excluding comments):"
grep -in "trending" ~/.claude/skills/daily-papers/fetch_and_score.py || echo "  (none)"

echo "[2] user-config.json no 'trending':"
grep -ic "trending" ~/.claude/skills/_shared/user-config.json

echo "[3] daily-papers-fetch/SKILL.md no 'trending':"
grep -ic "trending" ~/.claude/skills/daily-papers-fetch/SKILL.md

echo "[4] daily-papers-review/SKILL.md no 'trending':"
grep -ic "trending" ~/.claude/skills/daily-papers-review/SKILL.md

echo "[5] unit tests:"
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py | tail -2

echo "[6] integration (per Task 9):"
echo "  see /tmp/fetch_stderr.log + /tmp/daily_papers_top30.json + /tmp/daily_papers_search_meta.json"
```

Expected: all "no trending" greps return `0`; unit tests report `7 / 7 passed`.

- [ ] **Step 2: Write completion note**

Use Write tool to create `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-cut-hf-trending-COMPLETION.md`:

```markdown
# Spec #1 Completion — 2026-05-20

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-cut-hf-trending-design.md`
**Plan:** `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-cut-hf-trending.md`

## Files changed
- `~/.claude/skills/_shared/user-config.json` (removed `trending_age_exemption_upvotes`)
- `~/.claude/skills/daily-papers/fetch_and_score.py` (8 edits)
- `~/.claude/skills/daily-papers-fetch/SKILL.md`
- `~/.claude/skills/daily-papers-review/SKILL.md`

## Files created
- `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md` (backup archive)
- `/Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py` (unit test)

## Acceptance §9 status
- [x] fetch_and_score.py: 0 'trending' refs
- [x] user-config.json: 0 'trending' refs
- [x] daily-papers-fetch/SKILL.md: 0 'trending' refs
- [x] daily-papers-review/SKILL.md: 0 'trending' refs
- [x] Unit tests: 7/7 PASS
- [x] Integration: every paper in /tmp/daily_papers_top30.json has published >= age_cutoff (no leak)

## Pending follow-ups
- spec #0 (repo restructure) — see spec #1 §11
- spec #2 (PDF skill) — per audit roadmap
- spec #3 (Phase 5.5 pipeline_guard) — per audit roadmap
- spec #4 (Semantic Scholar / OpenAlex enrichment) — per audit roadmap
```

Replace any `- [x]` with `- [ ]` if Step 1 found violations; in that case STOP and return to the failing task.

---

## Notes for the engineer

1. **No git operations anywhere** in this plan. `~/.claude/skills/` is not a git repo (spec §8 / §11 explain). The backup archive at `_backup/hf-trending-removed-2026-05-20.md` IS the version control until spec #0 introduces git.

2. **TDD discipline**: Task 3 writes failing tests BEFORE any edits. Don't be tempted to write tests after the edits — the FAIL → edit → PASS cycle is what proves the test is real.

3. **Edit tool gotchas for fetch_and_score.py**: Several edits have very similar surrounding context (the `# ── ... ──` separators repeat). If an Edit fails for non-uniqueness, expand `old_string` with more surrounding lines until it's unique.

4. **The `_parse_hf_item(item, source)` function** retains its `source` parameter even though only `"hf-daily"` is now passed. That's intentional — the param documents intent and lets a future "domain research" skill reuse the helper with a different source label.

5. **Multi-day mode (`--days 7`)**: Out of scope; this plan does NOT change multi-day behavior beyond what Task 5's edits to the merge function imply. The history-dedup-skipping multi-day branch stays as-is.

6. **Don't touch historical daily reports** (per spec §3.2). The 2026-05-19-retrofit report is preserved as-is.

7. **If a Task 9 step fails** because HF or arXiv API is down: skip Task 9 and complete the spec with unit-test evidence only. Note the deferred integration test in the completion file under "Pending follow-ups".
