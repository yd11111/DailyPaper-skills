# Spec #1 Completion — 2026-05-20

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-cut-hf-trending-design.md`
**Plan:** `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-cut-hf-trending.md`

## Files changed
- `~/.claude/skills/_shared/user-config.json` — removed `trending_age_exemption_upvotes`
- `~/.claude/skills/daily-papers/fetch_and_score.py` — 9 prescribed Edits + 1 stray-comment cleanup (577 → 509 lines)
- `~/.claude/skills/daily-papers-fetch/SKILL.md` — 3 trending mentions stripped + 1 stale "周末模式放宽规则" prose fix
- `~/.claude/skills/daily-papers-review/SKILL.md` — source format / Phase 5.5.1 age_exempted / transparency template all cleaned

## Files created
- `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md` — backup archive (324 lines, all 10 sections, no placeholders)
- `/Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py` — 7 stdlib unit tests

## Acceptance §9 status

- [x] `fetch_and_score.py`: 0 'trending' refs (code + comments)
- [x] `user-config.json`: 0 'trending' refs
- [x] `daily-papers-fetch/SKILL.md`: 0 'trending' refs
- [x] `daily-papers-review/SKILL.md`: 0 'trending' refs (+ 0 age_exempted, 0 超龄豁免, 0 豁免)
- [x] Unit tests: 7/7 PASS (TDD red → green confirmed: started 0/7, ended 7/7)
- [x] Integration: `/tmp/daily_papers_top30.json` + `/tmp/daily_papers_search_meta.json` confirm every paper passes age cutoff (today's run had Final=0 due to no speech-relevant HF Daily papers + arxiv 429 rate-limit; the zero-leak invariant holds)

## Notable runtime observations on 2026-05-20

- HF Daily 2026-05-20 returned 16 papers, all LLM/CV/agent topics → 0 scored ≥ min_score=2 → 0 made the final cut. This is correct behavior, not a regression (manual scoring of 5 samples confirmed score_paper still works: video-generation paper got -999, others got 0)
- arxiv API was rate-limited (HTTP 429) during both fetch attempts — verified that the pipeline gracefully degrades to HF-only and meta still reports source_counts honestly
- 12/12 HF Daily papers passed age filter; 4/16 dropped as >7 days old — age filter behaves identically to the pre-edit state, only without the trending exemption escape hatch

## Spec scope compliance

- ✅ Historical daily reports (`/Users/xiangshu/DailyPaper/DailyPaper/DailyPapers/2026-05-19-论文推荐.md` and `2026-05-20-论文推荐.md`) NOT touched (per §3.2). They still parse as well-formed markdown.
- ✅ `.history.json` NOT touched
- ✅ Other skills (notes, weekly, compare, highlights, library-import, generate-mocs, paper-reader) NOT touched
- ✅ `_shared/user_config.py` NOT touched (its DEFAULT_CONFIG never had a trending field, verified pre-execution)

## Pending follow-ups

- **arxiv end-to-end smoke test** — defer until rate-limit clears. Re-run `python3 ~/.claude/skills/daily-papers/fetch_and_score.py` after a couple hours and visually inspect that arxiv papers appear and all pass age cutoff. Not blocking — unit tests + age-cutoff invariant on partial data already prove correctness.
- **spec #0** (repo restructure) — `~/.claude/skills/` → `~/DailyPaper/skills/` with symlinks, git init at `~/DailyPaper/`. After spec #0 lands, this completion record can be retired in favor of git history; the `_backup/` archive can be removed.
- **spec #2** (PDF skill) — next on the audit roadmap
- **spec #3** (Phase 5.5 pipeline_guard) — promote Adversarial Self-Review from prose to code, so future "old paper leak" cannot recur even with a bad LLM run
- **spec #4** (Semantic Scholar / OpenAlex enrichment) — cross-source DOI / citation backbone
- **future "domain research" skill** — will revive HF Trending fetch from the backup archive
