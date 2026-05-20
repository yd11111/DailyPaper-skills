# Spec #3 Completion — 2026-05-20

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-pipeline-guard-design.md`
**Plan:** `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-pipeline-guard.md`

## What changed

- New `skills/_shared/pipeline_guard.py` (~250 lines, stdlib only) enforces 3 hard-fact checks:
  - **C1 date_cutoff**: every recommended paper `published_date >= meta.age_cutoff`
  - **C2 existing_note_wikilink**: `📒 **已有笔记**: [[xxx]]` must resolve to a real `.md` under `{NOTES_PATH}`
  - **C3 critique_evidence_triples**: ≥2 `Claim/Evidence/Confidence` per non-existing-note paper
- New `scripts/test_pipeline_guard.py` (~140 lines, subprocess-driven, stdlib only) — 7 tests
- New `scripts/fixtures/` (7 draft `.md` + `enriched.json` + `meta.json` + 2 stub `notes/*.md`) — 11 files
- `skills/daily-papers-review/SKILL.md` Phase 5.5 prose replaced with `pipeline_guard.py` invocation; new Phase 5.6 (LLM self-revision on guard fail); Phase 5.6.A now renders self-review block from guard JSON, not LLM-written
- 3 git commits in `~/DailyPaper/`:
  - `44df452` — spec #3: design + implementation plan docs
  - `51b0dbf` — spec #3: pipeline_guard.py + 7 unit tests + 7 fixtures
  - `7f31947` — spec #3: review skill Phase 5.5 calls pipeline_guard.py + new Phase 5.6 self-revision

## Acceptance §7 status

- [x] [1] guard exists + imports cleanly; 5 expected functions present
- [x] [2] guard tests **7/7 PASS**
- [x] [3] review SKILL.md updated: pipeline_guard.py mentioned 4×, Phase 5.6 heading present, no stale prose
- [x] [4] **end-to-end retrofit verified**: 2026-05-19 fixture draft (containing VibeVoice 2025-08, OmniFlatten 2024-10, MiniCPM-o 2026-04) → guard exit=1 with 3 date_cutoff violations — exactly the historical leak now mechanically blocked
- [x] [5] spec #1 regression: `test_fetch_no_trending.py` still 7/7 PASS
- [x] [6] git commits committed in correct order
- [x] [7] working tree clean

## Notable observations

- **TDD flow worked exactly as designed**: 0/7 PASS (red) → skeleton 2/7 → C1 3/7 → C2 4/7 → C3 **7/7 PASS** (green). Each check provably worked in isolation before composing.
- **Spec regex bug caught + fixed during Task 7**: the spec's `TRIPLE_BLOCK_HEADER_RE = r"🧪\s*\*\*锐评依据\*\*"` assumed `🧪 **锐评依据**` (emoji outside bold), but real fixtures (and real 2026-05-20 daily report) use `- **🧪 锐评依据**:` (bold wraps emoji + text together). Fix: relaxed regex to `r"🧪[\s\*]*锐评依据"` — matches both shapes.
- **Plan grep check mismatch (cosmetic only)**: Task 9 expected `对抗式自查 >= 1` in updated SKILL.md, but the new wording uses the English "Adversarial Self-Review" (in details summary) and renamed the heading to "强制自查". Semantic equivalent preserved; substantive change correct.
- **Retrofit fixture preserved as regression hedge**: `scripts/fixtures/draft_retrofit_2026-05-19.md` will catch any future spec change that weakens date enforcement.

## Spec scope compliance

- ✅ Other skills (paper-reader, library-import, compare, highlights, notes, weekly, generate-mocs) untouched
- ✅ `fetch_and_score.py`, `enrich_papers.py` untouched
- ✅ `test_fetch_no_trending.py` (spec #1) untouched; still 7/7 PASS
- ✅ Historical daily reports under `DailyPaper/DailyPapers/` untouched
- ✅ guard does NOT enforce semantic checks (over-claim, contradiction) — LLM still owns 5.5.A/5.5.B per spec design

## Pending follow-ups

- **spec #2** (PDF skill) — central pdftotext/pdfimages/pdftoppm/pdfplumber wrapper. Now goes through git repo directly.
- **spec #4** (Semantic Scholar / OpenAlex enrichment) — DOI cross-source; may extend C1 to handle non-arxiv sources via `--source-resolver`
- **end-to-end run with real LLM** — wait for arxiv 429 to clear, then trigger `今日论文推荐` once and confirm review skill's new Phase 5.5/5.6 wires correctly in production
- **`skills/_backup/hf-trending-removed-2026-05-20.md`** can be deleted now (3 spec #3 commits = trustworthy git history). Defer to a later micro-cleanup spec.
- **Optional**: set `git config --global user.email/name` to suppress auto-attribution warnings on commits.

## Hole closed

The 2026-05-19 retrofit incident — where 3 old papers (OmniFlatten 2024-10, MiniCPM 2026-04, VibeVoice 2025-08) leaked into the daily report and had to be manually deleted — is now mechanically blocked. Any future review LLM run with similar drift would have guard exit=1 + 3 date_cutoff violations + LLM self-revision (Phase 5.6) → blocked save if even self-revision fails. The user no longer has to be the last line of defense.
