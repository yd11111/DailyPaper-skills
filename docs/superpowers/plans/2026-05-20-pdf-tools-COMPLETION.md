# Spec #2 Completion — 2026-05-20

**Spec:** `/Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-pdf-tools-design.md`
**Plan:** `/Users/xiangshu/DailyPaper/docs/superpowers/plans/2026-05-20-pdf-tools.md`

## What changed

- New `skills/_shared/pdf_tools.py` (~95 lines, stdlib only):
  - `extract_text(input, first_n_pages, timeout)` — auto-detects URL vs path
  - `extract_images(pdf_path, out_dir, prefix, min_size_bytes)` — pdfimages + size filter
  - `_check_binary(name)` — raises RuntimeError when pdftotext / pdfimages / curl missing
- New `scripts/test_pdf_tools.py` (~140 lines, stdlib + subprocess + importlib monkey-patch) — 6 tests, all PASS
- New `scripts/fixtures/_generate_sample_pdf.py` (~40 lines, requires reportlab) + `scripts/fixtures/sample.pdf` (~470 KB, 2 pages, embedded HuBERT figure)
- Migrated 3 callers — each now imports `pdf_tools` via the sibling `_shared` path pattern:
  - `skills/library-import/build_manifest.py.extract_first_page` — 8-line try/subprocess → 1-line call
  - `skills/daily-papers/download_note_images.py.try_pdf_extract` — async pdfimages block → `asyncio.to_thread(pdf_tools.extract_images, ...)` (plus orphan `prefix` var cleanup)
  - `skills/daily-papers/enrich_papers.py.extract_affiliations_pdf` — 3-stage shell pipe → 2-stage (pdf_tools.extract_text then stdin to extract_affiliations.py)
- 5 git commits:
  - `spec #2: design + implementation plan docs` (0587b91)
  - `spec #2: pdf_tools.py + 6 unit tests + sample.pdf fixture` (efab286)
  - `spec #2: build_manifest.py uses pdf_tools.extract_text` (f2aa9f5)
  - `spec #2: daily-papers callers use pdf_tools` (7631371)
  - `spec #2 completion record` (this commit)

## Acceptance §7 status

- [x] `pdf_tools.py` imports + signatures match spec §4.1
- [x] pdf_tools tests **6/6 PASS**
- [x] `build_manifest.py` migrated (pdf_tools imported; no direct pdftotext subprocess in extract_first_page)
- [x] `download_note_images.py` migrated (pdf_tools imported; no direct pdfimages subprocess)
- [x] `enrich_papers.py` migrated (pdf_tools imported; no `pdftotext -l 2` shell pipe)
- [x] spec #1 regression: `test_fetch_no_trending.py` still 7/7 PASS
- [x] spec #3 regression: `test_pipeline_guard.py` still 7/7 PASS
- [x] working tree clean; 5 spec #2 commits on top of prior spec history

## Notable observations

- TDD red→green clean: 6/6 ERROR initially (module missing) → 6/6 PASS after module implementation. The monkey-patched binary-missing test required `importlib.reload` to re-run `_check_binary` against the patched `shutil.which`. The plan's original `_import_module()` (using `spec_from_file_location`) made `reload` fail because the module wasn't findable by `PathFinder`; switched to `importlib.import_module` with `sys.path.insert(0, _SHARED_DIR)` so reload works. Test assertions unchanged.
- The `extract_affiliations_pdf` migration trades a 3-stage shell pipe for a 2-stage Python pipeline. Behavior is preserved: same retries (N=3 default), same per-attempt sleep (3s × attempt), same stdin-driven extract_affiliations.py call. Smoke against arxiv deferred until network 429 clears (informational, not blocking).
- Old `> 10240` byte filter in download_note_images became `>= 10240` in the new pdf_tools API (1-byte difference, no practical impact). All extracted PDF figures in the wild are kilobytes, not single bytes.
- reportlab is a fixture-generation dep only — not imported by pdf_tools or any runtime code. The `sample.pdf` is committed to git so future test runs don't need reportlab.
- Sample.pdf came out at ~470 KB rather than the plan's loose 30–300 KB target because the embedded HuBERT PNG is already ~470 KB and reportlab can't compress it further. All 6 fixture verification checks pass — flagging the size discrepancy but not regenerating.

## Spec scope compliance

- ✅ `extract_affiliations.py` unchanged (still stdin → JSON stdout)
- ✅ No pdfplumber / pdftoppm added
- ✅ library-import `.pdf.md` bug + Step 3.3 prose untouched (separate spec)
- ✅ paper-reader prose untouched
- ✅ Other skills + historical reports + inner vault untouched
- ✅ Spec #1 + #3 unit tests untouched and still 7/7

## Pending follow-ups

- **arxiv-live smoke for extract_affiliations_pdf / try_pdf_extract** — once arxiv 429 clears, run `今日论文推荐` end-to-end; verify enriched.json's `affiliations` field is populated for at least 1 paper and that any "PDF fallback" image extraction in daily-papers-notes still works through `try_pdf_extract`.
- **spec #4** — Semantic Scholar / OpenAlex DOI enrichment. May call `pdf_tools.extract_text(doi_url, first_n_pages=2)` for non-arxiv sources; pdf_tools is ready.
- **library-import full refactor** — `.pdf.md` empty-file bug + Step 3.3 self-contradiction in SKILL.md prose. Separate spec; will likely use `pdf_tools.extract_images` as a last-resort figure fallback.
- **`skills/_backup/hf-trending-removed-2026-05-20.md`** still redundant; can be deleted in a later micro-cleanup.

## Hole closed (partial)

This spec resolves the audit's P1-1 ("抽 `_shared/pdf_tools.py`：封 pdftotext/pdfimages/pdftoppm 三函数，所有 skill 统一调"). All 3 known callers now go through one module — future PDF-related bug fixes touch 1 file instead of 3, and spec #4 / future PDF skills inherit the same error model.
