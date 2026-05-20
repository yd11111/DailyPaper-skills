# Repo Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move all 12 paper-related skill directories from `~/.claude/skills/` into `~/DailyPaper/skills/`, replace originals with absolute-path directory symlinks, then `git init` at `~/DailyPaper/` so all future paper-system changes go through git.

**Architecture:** Two-phase atomic move. **Phase A** (reversible): `cp -a` each skill to the new location, byte-diff verify each copy. **Phase B** (point of no return): `rm -rf` each original then `ln -s` to the new location, all 12 in immediate succession. Then regression-gate on spec #1's 7-test suite to prove imports still resolve through symlinks. Only after green: `git init`, write `.gitignore`, explicit `git add` (not `git add .`), human-review `git status`, single initial commit.

**Tech Stack:**
- bash + coreutils: `cp -a`, `diff -rq`, `ln -s`, `rm -rf`
- `git` 2.x
- Python 3 (only to re-run the regression test)
- No new dependencies installed

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-repo-restructure-design.md`

---

## File Structure

**Directories MOVED (12, real path changes from `~/.claude/skills/` → `~/DailyPaper/skills/`):**
- `_backup/`
- `_shared/`
- `daily-papers/`
- `daily-papers-fetch/`
- `daily-papers-notes/`
- `daily-papers-review/`
- `daily-papers-weekly/`
- `generate-mocs/`
- `library-import/`
- `paper-compare/`
- `paper-highlights/`
- `paper-reader/`

**Symlinks CREATED (12, at `~/.claude/skills/<name>`):**
- Each `<name>` → absolute path `/Users/xiangshu/DailyPaper/skills/<name>`

**Files CREATED:**
- `/Users/xiangshu/DailyPaper/.gitignore` (~25 lines, exact content in Task 7)
- `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-repo-restructure-COMPLETION.md` (acceptance record, written in Task 11)

**Files NOT MODIFIED (per spec §3.2):**
- Any file *content* under the moved skill directories (this is a pure move; bytes unchanged)
- `~/DailyPaper/DailyPaper/` (inner Obsidian vault, has its own git, gitignored at outer)
- `~/DailyPaper/scripts/*.log` (kept on disk, gitignored)
- `~/DailyPaper/scripts/*.sh`, `*.py` (committed as-is)
- `~/DailyPaper/.claude/settings.json` (committed as-is; contains HF_ENDPOINT + SSL_CERT_FILE env vars)
- `~/Library/LaunchAgents/com.xiangshu.dailypaper{,.weekly}.plist` (untouched; they reference `~/DailyPaper/scripts/daily.sh` whose path doesn't change)

**Out-of-scope cleanup (defer):**
- No README written
- No log files deleted
- `_backup/` stays in `~/DailyPaper/skills/_backup/` (not moved to `docs/backups/`)
- `scripts/` not reorganized

---

## Task 1: Pre-flight verification

**Files:** read-only

- [ ] **Step 1: Confirm baseline — spec #1 tests 7/7 PASS BEFORE move**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py
echo "exit=$?"
```

Expected: `7 / 7 passed` and `exit=0`. **If not 7/7, STOP** — the regression baseline is broken before we start, so we can't tell if the move broke anything vs. it was already broken.

- [ ] **Step 2: Confirm 12 paper-skill dirs exist in `~/.claude/skills/`**

Run:
```bash
expected="_backup _shared daily-papers daily-papers-fetch daily-papers-notes daily-papers-review daily-papers-weekly generate-mocs library-import paper-compare paper-highlights paper-reader"
for s in $expected; do
  if [ ! -d "/Users/xiangshu/.claude/skills/$s" ]; then
    echo "MISSING: $s"
    exit 1
  fi
done
echo "All 12 source dirs present."
ls /Users/xiangshu/.claude/skills/ | wc -l
```

Expected: `All 12 source dirs present.` and `12`. If `ls | wc -l` reports more than 12, a new non-paper skill was added since spec #0 was written — STOP and re-confirm scope with user.

- [ ] **Step 3: Confirm target side is clean**

Run:
```bash
ls -la /Users/xiangshu/DailyPaper/skills/ 2>&1 | head -3
ls -la /Users/xiangshu/DailyPaper/.git 2>&1 | head -1
ls -la /Users/xiangshu/DailyPaper/.gitignore 2>&1
```

Expected: target `skills/` does not exist (or exists but is empty — verify with the ls), `.git` does not exist, `.gitignore` does not exist. If any of these already exist as non-empty, STOP — spec #0 assumes a clean slate.

- [ ] **Step 4: Confirm inner vault has its own git**

Run:
```bash
test -d /Users/xiangshu/DailyPaper/DailyPaper/.git && echo "inner vault git OK" || echo "MISSING"
```

Expected: `inner vault git OK`. If MISSING, the inner vault state has changed since spec #0 — STOP and verify with user.

- [ ] **Step 5: Record total size of source skills (for sanity reference after move)**

Run:
```bash
du -sh /Users/xiangshu/.claude/skills/
du -sk /Users/xiangshu/.claude/skills/*/ | sort -n
```

Record the total KB. Will compare against target after move.

---

## Task 2: Phase A — Create target dir and `cp -a` all 12 skills

**Files:**
- Create: `/Users/xiangshu/DailyPaper/skills/` (and 12 subdirs)

- [ ] **Step 1: Create target parent directory**

Run:
```bash
mkdir -p /Users/xiangshu/DailyPaper/skills
echo "created: $(test -d /Users/xiangshu/DailyPaper/skills && echo YES || echo NO)"
```

Expected: `created: YES`.

- [ ] **Step 2: `cp -a` all 12 skills**

Run:
```bash
set -e
skills="_backup _shared daily-papers daily-papers-fetch daily-papers-notes daily-papers-review daily-papers-weekly generate-mocs library-import paper-compare paper-highlights paper-reader"
for s in $skills; do
  src="/Users/xiangshu/.claude/skills/$s"
  dst="/Users/xiangshu/DailyPaper/skills/$s"
  cp -a "$src" "$dst"
  echo "copied: $s"
done
echo "Phase A copy complete."
```

`cp -a` preserves mode, ownership, timestamps, and follows symlinks-as-symlinks. `set -e` stops on first failure.

Expected: 12 "copied: <name>" lines followed by "Phase A copy complete." If any line fails to print, the cp errored — abort and report BLOCKED.

- [ ] **Step 3: Sanity — both sides now coexist**

Run:
```bash
ls /Users/xiangshu/.claude/skills/ | wc -l
ls /Users/xiangshu/DailyPaper/skills/ | wc -l
du -sh /Users/xiangshu/DailyPaper/skills/
```

Expected: both `wc -l` report `12`. Target `du -sh` total within ±5% of the source total recorded in Task 1 Step 5. (Small drift OK due to filesystem block rounding.)

---

## Task 3: Phase A — `diff -rq` verify all 12

**Files:** read-only verification

- [ ] **Step 1: Byte-level diff each skill**

Run (MUST be `bash -c` because zsh does NOT word-split unquoted `$skills` — discovered during Task 2 execution):
```bash
bash -c '
set -e
skills=(_backup _shared daily-papers daily-papers-fetch daily-papers-notes daily-papers-review daily-papers-weekly generate-mocs library-import paper-compare paper-highlights paper-reader)
failed=0
for s in "${skills[@]}"; do
  src="/Users/xiangshu/.claude/skills/$s"
  dst="/Users/xiangshu/DailyPaper/skills/$s"
  out=$(diff -rq "$src" "$dst" 2>&1)
  if [ -n "$out" ]; then
    echo "DIFF FOUND for $s:"
    echo "$out"
    failed=$((failed + 1))
  else
    echo "ok: $s"
  fi
done
echo "Phase A verify: $failed failures out of 12"
test $failed -eq 0
'
```

`diff -rq` recursively compares two directories and prints only filenames that differ (silent on identical). The `bash -c` wrapper + bash array is mandatory; under default zsh `for s in $skills` would loop ONCE with all 12 names concatenated.

Expected: 12 "ok: <name>" lines, "Phase A verify: 0 failures out of 12", and exit 0. **If failed > 0, STOP and report BLOCKED** — do NOT proceed to Phase B. The originals are still intact in `~/.claude/skills/`, so the system is fully functional; remove the partial copies under `~/DailyPaper/skills/` and investigate.

---

## Task 4: Phase B — `rm -rf` originals and `ln -s` symlinks

⚠️ **Point of no return.** This task removes the originals. Only execute after Task 3 reports 0 failures. Once started, run all 12 to completion — a partial state will hide some skills from Claude Code.

**Files:**
- Delete: `/Users/xiangshu/.claude/skills/<12 names>/` (real dirs)
- Create: `/Users/xiangshu/.claude/skills/<12 names>` (symlinks)

- [ ] **Step 1: Atomic rm + ln for all 12**

Run (MUST be `bash -c` per Task 3 note):
```bash
bash -c '
set -e
skills=(_backup _shared daily-papers daily-papers-fetch daily-papers-notes daily-papers-review daily-papers-weekly generate-mocs library-import paper-compare paper-highlights paper-reader)
for s in "${skills[@]}"; do
  src="/Users/xiangshu/.claude/skills/$s"
  dst="/Users/xiangshu/DailyPaper/skills/$s"
  rm -rf "$src"
  ln -s "$dst" "$src"
  echo "linked: $s -> $dst"
done
echo "Phase B complete."
'
```

Expected: 12 "linked: <name> -> /Users/xiangshu/DailyPaper/skills/<name>" lines and "Phase B complete." If any iteration errors, the system is in a mixed state — note which skill(s) failed and either re-run the failing step or restore from the target dir (`cp -a /Users/xiangshu/DailyPaper/skills/<name> /Users/xiangshu/.claude/skills/<name>`).

- [ ] **Step 2: Verify all 12 are symlinks pointing to correct targets**

Run (bash array, same reason as above):
```bash
bash -c '
skills=(_backup _shared daily-papers daily-papers-fetch daily-papers-notes daily-papers-review daily-papers-weekly generate-mocs library-import paper-compare paper-highlights paper-reader)
ok=0
for s in "${skills[@]}"; do
  link="/Users/xiangshu/.claude/skills/$s"
  expected="/Users/xiangshu/DailyPaper/skills/$s"
  if [ -L "$link" ] && [ "$(readlink "$link")" = "$expected" ]; then
    ok=$((ok + 1))
  else
    echo "BAD: $s — type=$(stat -f %ST "$link" 2>/dev/null || echo missing) readlink=$(readlink "$link" 2>/dev/null)"
  fi
done
echo "$ok / 12 symlinks correct"
'
```

Expected: `12 / 12 symlinks correct` and no "BAD:" lines.

- [ ] **Step 3: Verify the symlink-side directory listing is now ~5 KB total**

Run:
```bash
du -sh /Users/xiangshu/.claude/skills/
ls -la /Users/xiangshu/.claude/skills/
```

Expected: total size << 100 KB (just the symlink inodes + metadata). `ls -la` should show every entry as `lrwxr-xr-x` with `-> /Users/xiangshu/DailyPaper/skills/<name>`.

---

## Task 5: Regression — spec #1 unit tests must still 7/7 PASS

**Files:** read-only

- [ ] **Step 1: Run the same 7 tests as the baseline**

Run:
```bash
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py
echo "exit=$?"
```

Expected: `7 / 7 passed` and `exit=0`. Identical result to Task 1 Step 1.

**If any test FAILs:** this proves the symlinks are not transparent to the import path. Diagnose by running a single import:
```bash
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('f', '/Users/xiangshu/.claude/skills/daily-papers/fetch_and_score.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('import OK')
"
```
If that import fails with `ModuleNotFoundError: user_config`, the `_shared` sibling import is broken via the symlink. Report BLOCKED and surface the path resolution details (`Path(__file__).resolve()` output).

---

## Task 6: End-to-end smoke test

**Files:** read-only

- [ ] **Step 1: Run fetch script to confirm runtime path resolution**

Run:
```bash
python3 /Users/xiangshu/.claude/skills/daily-papers/fetch_and_score.py > /tmp/spec0_smoke.json 2> /tmp/spec0_smoke.err
echo "exit=$?"
head -10 /tmp/spec0_smoke.err
```

Expected: `exit=0`. stderr shows `Fetching hf-daily ...`, `HF: N papers after scoring`, possible arxiv 429 warning, and `Search meta saved: /tmp/daily_papers_search_meta.json`.

**If `ModuleNotFoundError` or `FileNotFoundError`:** STOP — symlink path resolution is broken in some way. Likely cause: `_shared/user_config.py` reads a config file via a path that doesn't resolve through the symlink correctly. Report BLOCKED with full traceback.

- [ ] **Step 2: Verify output JSON parses**

Run:
```bash
python3 -c "
import json
data = json.load(open('/tmp/spec0_smoke.json'))
print(f'papers: {len(data)}')
meta = json.load(open('/tmp/daily_papers_search_meta.json'))
print(f'sources: {meta.get(\"source_breakdown_of_final\")}')
"
```

Expected: prints `papers: N` (N ≥ 0; 0 is acceptable since today's HF Daily may have no speech-relevant papers) and `sources: {...}` showing only `hf-daily` and `arxiv` keys (spec #1 invariant preserved).

---

## Task 7: Write `.gitignore`

**Files:**
- Create: `/Users/xiangshu/DailyPaper/.gitignore`

- [ ] **Step 1: Write the file**

Use Write tool to create `/Users/xiangshu/DailyPaper/.gitignore` with EXACTLY this content:

```gitignore
# 内层 Obsidian vault 自带 git 仓库，外层不跟踪
DailyPaper/

# 运行时日志
*.log
scripts/*.log

# Python 编译产物
__pycache__/
*.pyc
*.pyo

# macOS
.DS_Store

# Claude Code 本地覆盖配置（环境特异）
.claude/settings.local.json
.claude/*.local.json

# 临时 / 缓存
/tmp/
*.tmp
*.swp
```

- [ ] **Step 2: Sanity check the file exists and is non-empty**

Run:
```bash
wc -l /Users/xiangshu/DailyPaper/.gitignore
head -3 /Users/xiangshu/DailyPaper/.gitignore
```

Expected: line count > 15; first 3 lines visible.

---

## Task 8: `git init` and stage explicit paths

**Files:** init `/Users/xiangshu/DailyPaper/.git/`

- [ ] **Step 1: Run `git init`**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git init
```

Expected: `Initialized empty Git repository in /Users/xiangshu/DailyPaper/.git/` (or `Reinitialized` if .git existed — but Task 1 Step 3 already confirmed it didn't).

- [ ] **Step 2: Explicitly add the 4 tracked top-level items**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git add .gitignore skills/ scripts/ docs/ .claude/settings.json
echo "exit=$?"
```

⚠️ **Do NOT use `git add .` or `git add -A`** — those could accidentally stage the inner vault (gitignored, but the safety net is `git add -A` would also try to stage things we didn't list). The explicit list is the safety belt.

Expected: `exit=0`. The `.gitignore` rule will keep `DailyPaper/` (inner vault) out of staging even though we didn't list it.

- [ ] **Step 3: Human-review `git status` BEFORE commit**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git status
```

Read the output carefully. The "Changes to be committed" list should include:
- `new file: .gitignore`
- `new file: .claude/settings.json`
- many `new file: docs/...` entries
- many `new file: scripts/...` entries (but NO `scripts/*.log` — those are gitignored)
- many `new file: skills/...` entries (recursively across 12 skill dirs)

The list MUST NOT include:
- `DailyPaper/` or anything under `DailyPaper/...` (inner vault)
- `*.log` files
- `__pycache__/` or `*.pyc`
- `.DS_Store`

**If you see any forbidden item in the staged list, STOP.** Investigate `.gitignore` correctness, then `git rm --cached <bad path>` to unstage, re-status, and only commit when clean.

- [ ] **Step 4: Programmatically confirm no forbidden paths staged**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git diff --cached --name-only | grep -E '^DailyPaper/|\.log$|__pycache__|\.DS_Store$' && echo "FORBIDDEN STAGED" || echo "clean"
```

Expected: `clean` (the `grep` finds nothing → exits 1 → `||` branch runs).

---

## Task 9: Initial commit

**Files:** create commit

- [ ] **Step 1: Commit with descriptive message**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git commit -m "import paper system from ~/.claude/skills/ (spec #0)

Per spec #0 (docs/superpowers/specs/2026-05-20-repo-restructure-design.md):
- Moved 12 paper skill dirs from ~/.claude/skills/ to skills/
- Original locations now symlinks pointing back to skills/<name>
- Includes spec #1 result (HF Trending removal, backup in skills/_backup/)
- Inner Obsidian vault DailyPaper/ excluded via .gitignore

🤖 Generated with Claude Code"
echo "exit=$?"
```

Expected: `exit=0`. Commit message echoed back with file count.

- [ ] **Step 2: Verify clean working tree**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git status
```

Expected: `nothing to commit, working tree clean`.

- [ ] **Step 3: Verify commit shape**

Run:
```bash
cd /Users/xiangshu/DailyPaper && git log --stat -1 | tail -30
cd /Users/xiangshu/DailyPaper && git log --stat -1 | grep -c "^ DailyPaper/"
```

Expected:
- First command shows the commit summary plus a list of created files (mostly under `skills/`, `scripts/`, `docs/`, plus `.gitignore` and `.claude/settings.json`)
- Second command outputs `0` (no inner-vault paths leaked into commit; the leading space in `^ DailyPaper/` matches the `--stat` format `" <path> | N +"` for files in DailyPaper/, but excludes our outer `skills/`). `grep -c` exits 1 when count is 0 — that's normal, ignore exit code.

---

## Task 10: Acceptance verification (spec §6 checklist)

**Files:** read-only

- [ ] **Step 1: Run all 8 acceptance checks at once**

Run:
```bash
echo "=== Spec §6 Acceptance ==="
echo
echo "[1] ls ~/.claude/skills/ shows 12 symlinks, no regular dirs:"
ls -la /Users/xiangshu/.claude/skills/ | tail -n +4 | awk '{print $1, $9, $10, $11}'
echo "  (every line should start with 'l' for symlink)"
echo
echo "[2] readlink one specific symlink:"
readlink /Users/xiangshu/.claude/skills/daily-papers
echo "  (should equal: /Users/xiangshu/DailyPaper/skills/daily-papers)"
echo
echo "[3] sizes — symlink side tiny, target side carries content:"
du -sh /Users/xiangshu/.claude/skills/
du -sh /Users/xiangshu/DailyPaper/skills/
echo
echo "[4] ls target shows 12 real dirs:"
ls /Users/xiangshu/DailyPaper/skills/ | wc -l
echo "  (should equal 12)"
echo
echo "[5] regression: 7/7 unit tests:"
python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py | tail -2
echo
echo "[6] smoke import:"
python3 /Users/xiangshu/.claude/skills/daily-papers/fetch_and_score.py >/dev/null 2>&1 && echo "  exit=0 OK" || echo "  exit=non-zero — possibly arxiv 429, check stderr"
echo
echo "[7] git status clean:"
cd /Users/xiangshu/DailyPaper && git status --porcelain | wc -l
echo "  (should be 0)"
echo
echo "[8] no inner-vault path in first commit (grep -c exits 1 when count is 0, that's normal):"
cd /Users/xiangshu/DailyPaper && (git log --stat -1 | grep -c "^ DailyPaper/" || true)
echo "  (should be 0)"
echo
echo "[9] all 5 required path prefixes present in commit:"
for p in "skills/" "scripts/" "docs/" ".gitignore" ".claude/settings.json"; do
  cnt=$(cd /Users/xiangshu/DailyPaper && git log --stat -1 | grep -c "$p")
  echo "  $p: $cnt"
done
```

Read the output and verify each item against the expected value in parentheses.

---

## Task 11: Write COMPLETION note

**Files:**
- Create: `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-repo-restructure-COMPLETION.md`

- [ ] **Step 1: Write the completion file**

Use Write tool to create `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-repo-restructure-COMPLETION.md` with this content (adjust the numbers in `[fill in from Task 10]` sections to actual values you observed):

```markdown
# Spec #0 Completion — 2026-05-20

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-repo-restructure-design.md`
**Plan:** `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-repo-restructure.md`

## What changed

- All 12 paper skill dirs moved from `~/.claude/skills/<name>/` to `~/DailyPaper/skills/<name>/`
- `~/.claude/skills/<name>` now holds 12 absolute-path directory symlinks pointing to the new locations
- `~/DailyPaper/` is now a git repository, initial commit captures the post-spec-#1 state

## Acceptance §6 status (from Task 10)

- [x] [1] `~/.claude/skills/` shows 12 symlinks, no regular dirs
- [x] [2] readlink resolves correctly for spot-checked skill
- [x] [3] symlink side is small; target side carries content (sizes: [fill in from Task 10])
- [x] [4] target dir has 12 real subdirs
- [x] [5] regression: 7/7 unit tests PASS (same as baseline)
- [x] [6] smoke import: fetch_and_score.py runs without ImportError (arxiv 429 acceptable)
- [x] [7] `git status` clean
- [x] [8] no inner-vault path in first commit
- [x] [9] all 5 required path prefixes present in commit

## Spec scope compliance

- ✅ Inner vault `~/DailyPaper/DailyPaper/` untouched
- ✅ `scripts/*.log` not deleted (per spec §3.2)
- ✅ `~/.claude/settings.json` committed as-is (no content change)
- ✅ No README written
- ✅ `_backup/` kept under `~/DailyPaper/skills/_backup/`, not moved to `docs/backups/`
- ✅ LaunchAgents not modified

## Notable observations

- Skill file contents unchanged (verified via `diff -rq` in Task 3 before any rm)
- spec #1 unit test result is byte-identical before and after the move
- [fill in any unexpected behavior or surprises observed during execution]

## Pending follow-ups

- **spec #2** (PDF skill) — now goes through this git repo
- **spec #3** (Phase 5.5 pipeline_guard) — same
- **spec #4** (Semantic Scholar / OpenAlex enrichment) — same
- **future cleanup**: `skills/_backup/hf-trending-removed-2026-05-20.md` is now redundant (git history holds prior state); can be deleted in a later spec
- **arxiv smoke from spec #1 §6.2** — still pending until rate limit clears
```

- [ ] **Step 2: Final hand-back to user**

After writing the completion file, report:
- Spec #0 done
- All Task 10 acceptance items passed
- Next available specs: #2 (PDF skill), #3 (pipeline_guard), #4 (Semantic Scholar enrichment)

---

## Notes for the engineer

1. **The cp+verify gate (Tasks 2–3) is reversible.** If verify fails, just `rm -rf ~/DailyPaper/skills/` and you're back to the pre-spec state. Don't proceed to Task 4 until Task 3 reports 0 failures.

2. **Task 4 is the point of no return.** Once you start rm-ing originals, you must complete all 12 rm+ln pairs immediately. A new Claude Code session that runs while you're mid-Task-4 would see partial skills missing. The window is <5 seconds for 12 small dirs.

3. **The `_shared/__pycache__/` from spec #1 will move with the rest.** That's fine — `__pycache__` is gitignored, so it won't be committed; on first next Python run, fresh bytecode is regenerated under the symlinked path.

4. **Why `cp -a` and not `cp -r`?** `cp -a` preserves mode/owner/timestamps and treats symlinks as symlinks rather than dereferencing. Important if any skill has an internal symlink (none currently do, but this guards future additions).

5. **`set -e` in bash loops.** Each `for ...; do ... done` block above uses `set -e` so the first error aborts the loop. Without it, a mid-loop failure would silently continue and leave you with partial state.

6. **macOS `stat -f %ST`** in Task 4 Step 2 yields the file type (`l` for symlink). On Linux you'd use `stat -c %F`. This plan targets macOS only.

7. **No git for `~/.claude/skills/` itself.** The symlinks live there but it's still not a git repo. That's fine — the real content lives in `~/DailyPaper/skills/` which IS a git repo. If you accidentally `git init` at `~/.claude/skills/`, just `rm -rf ~/.claude/skills/.git`.

8. **If you need to add a new non-paper skill in the future**, install it at `~/.claude/skills/<new-name>/` as a real directory. It will sit alongside the 12 paper symlinks without conflict.
