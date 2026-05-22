# DailyPaper Audit Roadmap

> 集中追踪所有"该做但还没做"的事。每个 spec 完成后回来打勾 / 补条目；
> 新 spec 开工前先扫一眼这里有没有更高优的事被压住。

- **建立日期**：2026-05-21（spec #2 收尾时一次性整理）
- **最后更新**：2026-05-22
- **来源**：4 份 `*-COMPLETION.md` 的 "Pending follow-ups" + 一次完整代码审计
- **维护方式**：完成一条就标 `[x]` 并写"由 spec #N 关闭"，不要删；累积形成历史
- **当前进度**：P1 全部关闭（11/11）；P2 关闭 17/19（P2-3 wontfix、P2-8 降级 nice-to-have）；P3 全部关闭（9/9）；spec #5 已完成；测试 149 pass

---

## 已完成的 spec

- [x] **spec #0** — repo 重构：git init 外层 + skills 从 `~/.claude/` 迁到 `~/DailyPaper/skills/` 经 symlink
- [x] **spec #1** — 砍掉 HF Trending 抓取（只留 HF Daily + arxiv）
- [x] **spec #2** — `_shared/pdf_tools.py` 集中封装 + 3 caller 迁移（关闭 audit P1-1）
- [x] **spec #3** — `pipeline_guard.py` 把对抗式自查从 prose 升到代码（关闭 audit P1-2）

---

## 进行中 / 已规划的 spec

- [x] **spec #4 — Semantic Scholar / OpenAlex DOI 富化**
  - 跨源主键（arxiv id 之外用 DOI 拉 affiliations / citations）
  - 新增 `_shared/scholarly_api.py`：S2 主 + OpenAlex 备，subprocess curl，Semaphore(1) 限速
  - `enrich_papers.py` 新增字段：doi / citation_count / influential_citation_count / venue / tldr
  - **状态**：已完成（2026-05-22）

- [x] **spec #5 — library-import 重构**
  - 修 `.pdf.md` 空文件 bug：Step 4 加明确 ⚠️ 提示目标是 .pdf 二进制文件
  - 修 SKILL.md Step 3.3 自相矛盾的 figure 处理流程：删除假的 `/tmp/library_figs` 引用
  - 新 Step 3.3：`pdf_tools.extract_images` fallback（WebFetch 失败时按文件大小取 top 3 图）
  - 消除"不抽图"与 Step 3.0 WebFetch 选图流程的矛盾
  - 修 Step 1 脚本路径（`~/.claude/skills/` → `~/DailyPaper/skills/`）
  - 清理 vault 中 2 个 0 字节 `.pdf.md` 遗留文件
  - **状态**：已完成（2026-05-22）

- [ ] **future「domain research」skill**
  - 把 spec #1 删掉的 HF Trending 抓取从 `_backup/` 复活，做"领域定向调研"
  - **状态**：等有需求再做，本身就被延期

---

## P1 审计发现（latent bug / 安全 / 静默错乱，必做）

### ~~P1-3~~ ✅ `extract_arxiv_id` 重复实现 6 次且有一处 regex 偏弱

**已修（2026-05-21）**：创建 `_shared/arxiv_id.py`（`extract_id` + `extract_all_ids`），统一 `\b(\d{4}\.\d{4,5})(?:v\d+)?\b` 带 vN 剥离。7 个 caller 全部迁移：fetch_and_score / download_note_images / enrich_papers / update_history / pipeline_guard / build_manifest / paper_daemon。同时清理了 download_note_images + build_manifest 中的 dead `import subprocess`。

### ~~P1-4~~ ✅ `enrich_papers.py` HTML 抽取 zero unit tests（584 行）

**已修（2026-05-21）**：新建 `scripts/test_enrich_html.py`，28 个测试覆盖 strip_tags / extract_figure_url（6 场景）/ extract_authors_html / extract_affiliations_html / extract_section_headers / extract_captions / extract_has_real_world / extract_method_names / extract_method_summary。
- **位置**：`skills/daily-papers/enrich_papers.py:131-312`
- **影响**：`extract_figure_url / extract_authors_html / extract_affiliations_html / extract_method_summary` 都是 regex；arxiv / HF 改 HTML 时静默退化为空 enrichment，pipeline 继续跑，用户只能凭"今天报告里没图"才发现
- **修复方向**：fixture 一批 HTML 片段 + 5-8 个 parser 测试

### ~~P1-5~~ ✅ `fetch_and_score.merge_and_dedup` zero unit tests

**已修（2026-05-21）**：新建 `scripts/test_merge_dedup.py`，10 个场景测试覆盖 age filter / merge-by-id / history dedup / multi-day skip / min_score / backfill / top_n cap / fallback_ids。
- **位置**：`skills/daily-papers/fetch_and_score.py:312-446`
- **影响**：「只抓真新论文」的核心逻辑——age filter / history dedup / min score / backfill。一次回归就会静默放老论文进去（5-19 incident 就是这样发生的）
- **修复方向**：fixture papers 数组 + 5-10 个 dedup 场景测试

### ~~P1-6~~ ✅ `library-import/build_manifest.py` zero unit tests

**已修（2026-05-22）**：新建 `scripts/test_build_manifest.py`，11 个测试覆盖 extract_first_page（valid/missing PDF）/ find_arxiv_id（4 场景）/ CLI JSON shape / topic 提取（subdir/root/_root）/ missing dir / empty dir。复用 spec #2 的 `sample.pdf` fixture。
- **位置**：整个文件
- **影响**：现状只有"用户跑没崩"算 pass；regex match / 重复名 / 缺 affiliations 等边界场景全靠肉眼
- **修复方向**：fixture 2-3 个 PDF（可重用 spec #2 的 sample.pdf）+ JSON 形状断言

### ~~P1-7~~ ✅ `DEFAULT_CONFIG` 是旧机器人方向（与用户当前方向**相反**）

**已修（2026-05-21）**：清空 `user_config.py:DEFAULT_CONFIG.daily_papers` 中的 keyword/category 列表，加注释解释。user-config.json 仍正确覆盖；missing config 会被 fetch_and_score.py 当成 0 关键词处理（loud failure：0 篇匹配），不再出现反向偏好。
- **位置**：`skills/_shared/user_config.py:38-100`
- **影响**：fallback 关键词是 `world model / embodied ai / 3d gaussian splatting / cs.RO/cs.CV/cs.AI/cs.LG`，且 `negative_keywords` 包含 `speech synthesis / text-to-speech`——即"屏蔽用户真正想要的论文"。一旦 `user-config.json` 丢失或损坏，pipeline 会用反向偏好静默运行
- **修复方向**：两条路二选一——(a) 删除 keyword 部分让 missing config 直接报错，(b) 把默认值刷新为 TTS/speech 方向

### ~~P1-8~~ ✅ `paper-reader/SKILL.md` 仍推荐直接 `pdfimages -png`

**已修（2026-05-21）**：line 114 改为推荐 `_shared/pdf_tools.extract_images(...)`（spec #2 集中化封装）。
- **位置**：`skills/paper-reader/SKILL.md:114`
- **影响**：spec #2 已把 PDF 工具集中化，但 paper-reader 这份 prose 还在引导 LLM 直接 shell out。每次 LLM 读这份 SKILL 都会去 reinvent the wheel
- **修复方向**：改成"import `pdf_tools.extract_images` 通过子进程或 `python -c`"，或干脆删掉那段（让 LLM 自己探索）

### ~~P1-9~~ ✅ `reorganize_notes.py` 是死代码且有**错误分类**

**已修（2026-05-21）**：`git rm skills/paper-reader/assets/reorganize_notes.py`。无外部 caller，删除安全。
- **位置**：`skills/paper-reader/assets/reorganize_notes.py`（458 行）
- **影响**：`CATEGORY_RULES` 是旧的机器人 taxonomy（`3-机器人策略 / 4-足式运动 / 6-3D视觉`...）。当前 vault 是 speech taxonomy（`1-TTS与语音合成`...）。**如果有人误跑这个脚本，会把所有语音笔记打散到 `_待整理/`**
- **修复方向**：删（推荐）或为新 taxonomy 重写

### ~~P1-10~~ ✅ `daily-papers-notes/SKILL.md` 质量 check 与 paper-reader 模板 drift

**发现于 2026-05-21 跑日报时**：daily-papers-notes 的 Step 2 质量验证要求 `## 实验结果` header，但 paper-reader 模板实际产出 `## 实验`——所有合格笔记都会被误判为不合格，触发"删除并重新生成"循环。

**已修（同日）**：`skills/daily-papers-notes/SKILL.md:102` 改为"`## 实验`（或 `## 实验结果`）任一即可"。

### ~~P1-11~~ ✅ `enrich_papers.py` 单 .json arg 语义 vs SKILL.md 不一致

**发现于 2026-05-21 跑日报时**：脚本把单个位置 `.json` arg 解析为 input，但 SKILL.md 示例 `cat top30 | enrich.py enriched.json` 中 `enriched.json` 是预期的 output——一次调用，两种语义，导致脚本首次跑读不存在的文件失败。

**已修（同日）**：`enrich_papers.py` 加 `stdin_piped = not sys.stdin.isatty()` 检测；当 stdin 有数据 + 1 arg 时，arg 当 OUTPUT；2 args 时保持 input+output 语义；auto-detect 默认输入文件仅在 stdin 未 pipe 时启用。4 种调用方式均验证通过。

### ~~Pipeline 自动化~~ ✅ 减少人工介入点

**已修（2026-05-21）**：
- `update_history.py`：修 weak regex + hardcoded path → 用 `daily_papers_dir()` + `arxiv_id.extract_all_ids`；写入 `daily-papers-review/SKILL.md` Phase 6 一行脚本调用
- `backfill_links.py`：改进 method-name 归一化（`_normalize_name` 去 `-_.` + 小写）；写入 `daily-papers-notes/SKILL.md` Step 3 一行脚本调用
- 流水线端到端验证：fetch(15) → enrich(15) → review(11) → guard pass → vault save → history update，全程零人工介入

---

## P2 审计发现（tech debt，应做）

### ~~P2-1~~ ✅ `INST_KEYWORDS` 机构关键词列表重复

**已修（2026-05-22）**：抽取 `_shared/affiliation_keywords.py`，`enrich_papers.py` 和 `extract_affiliations.py` 均改为 import。
- `skills/daily-papers/enrich_papers.py:79-97` + `skills/daily-papers/extract_affiliations.py:16-38`
- 加一个学校要改两处。抽 `_shared/affiliation_keywords.py`

### ~~P2-2~~ ✅ Zotero DB 辅助函数 2 处复制

**已修（2026-05-22）**：新建 `_shared/zotero_db.py`（8 个共享函数：`copy_readonly` / `get_all_child_collections` / `get_collection_path` / `find_collection` / `get_papers_in_collection` / `get_pdf_path` / `get_item_fields` / `get_item_collections`）。两个 caller 统一为 connection-passing 模式：
- `paper_daemon.py`：删除 5 个重复 Zotero 函数（-80 行），改为 4 个 thin wrappers 委托到 `_zotero`
- `zotero_helper.py`：删除 `copy_db` / `get_all_child_collections` / `get_collection_path` / `get_item_collections` 重复实现，`get_pdf_path` / `get_paper_info` / `find_collection_by_name` 改为委托 + CLI 输出层
- 写操作（`add_to_collection_db` / `remove_from_collection_db`）保留在 helper（直连真实 DB）

### P2-3：`sys.path` bootstrap 在 10 个文件里 copy-paste — **wontfix**
- 同样的 3 行 `_SHARED_DIR = ... / sys.path.insert(0, ...)` 出现 11 次
- 修复方向：(a) `_shared/` 加 `__init__.py` + `pyproject.toml` 当成包，或 (b) 一个 `_shared/bootstrap.py` 大家 import
- **决定**：保留现状。3 行 boilerplate 胜于引入 pyproject.toml 安装步骤或 bootstrap.py 的间接层。各 caller 深度不同（parent.parent vs parents[1] vs parents[2]），一个通用 bootstrap 反而更难理解

### ~~P2-4~~ ✅ `load_history` 实现 2 次，两个 schema owner

**已修（2026-05-22）**：新建 `_shared/history_store.py`（`load / save / append / prune`）。`fetch_and_score.py` 和 `update_history.py` 均改为 import，不再各自维护路径/读写逻辑。
- `fetch_and_score.py:288-294` + `update_history.py:40-48,51-55`
- 一个常量叫 `HISTORY_PATH`、一个叫 `HISTORY_FILE`，指同一文件
- 抽 `_shared/history_store.py`：`load() / append(entries, date) / prune(days)`

### ~~P2-5~~ ✅ method 名归一化逻辑分叉

**已修（2026-05-22）**：新建 `_shared/method_name.py`（`normalize()`），统一 subscript/Greek/&/标点处理。`paper_daemon.py` 和 `backfill_links.py` 均改为 import，backfill_links 获得了 π0.5 等场景的正确匹配能力。
- `paper_daemon.py:367-372` 处理下标 / 希腊字母 / `&→and` / 标点
- `backfill_links.py:46-47,105` 只 `.lower()`
- 后果：`π0.5.md` 在 paper_daemon 能匹配，在 backfill 永远匹配不上
- 抽 `_shared/method_name.py`

### ~~P2-6~~ ✅ `paper-reader/paper_daemon.py` 无测试（788 行，最大文件）

**已修（2026-05-22）**：新建 `scripts/test_paper_daemon.py`，20 个测试覆盖 detect_limit_error / parse_reset_wait_seconds / _normalize_method_name / _extract_note_method_names / title_matches_note（精确匹配/子串/短子串防误匹配/空输入）。
- 至少这些纯函数该测：`title_matches_note / _normalize_method_name / _extract_note_method_names / parse_reset_wait_seconds / detect_limit_error`

### ~~P2-7~~ ✅ `daily-papers-notes/backfill_links.py` 无测试

**已修（2026-05-22）**：新建 `scripts/test_backfill_links.py`，11 个测试覆盖 extract_method_name_from_title / match_papers_with_notes（find/skip/already-linked/normalized）/ backfill_links（insert/no-match）/ update_diversion_table。
- `match_papers_with_notes`（line 80）regex 脆弱；`update_diversion_table` 不 match 时静默部分更新

### P2-8：错误处理无统一策略，9 处 silent return — **降级为 P3**
- `enrich_papers.py:123,152,296`、`fetch_and_score.py:94`、`download_note_images.py:82,106,126,157`、`pdf_tools.py:43,45,60,66,69` 等
- 有的 print stderr 有的不，调用方区分不了"无数据" vs "binary 缺失 / crashed"
- **缓解措施（已完成）**：P2-10 收窄了 enrich_one 的 except（coding bug 不再被吞）；pdf_tools 的空返回是 by-design（caller 用空串判断"PDF 不可用"）
- 剩余价值：引入 logging module 可统一 level（但这些是 one-shot CLI，非长跑服务，`print(stderr)` 模式可接受）
- **状态**：降为 nice-to-have，不紧急

### ~~P2-9~~ ✅ `except (asyncio.TimeoutError, Exception)` 4 处冗余

**已修（2026-05-22）**：4 处统一改为 `except Exception:`。
- `Exception` 已经覆盖 `TimeoutError`，意图模糊
- 位置：`download_note_images.py:78,122,153`、`enrich_papers.py:120`
- 要么收窄（`OSError, SubprocessError`），要么直接 `except Exception`

### ~~P2-10~~ ✅ `enrich_one` 内层 except 吞所有错（含 coding bug）

**已修（2026-05-22）**：`enrich_one` 内层改为 `except (OSError, ValueError, UnicodeDecodeError)`；`extract_affiliations_pdf` 改为 `except (asyncio.TimeoutError, json.JSONDecodeError, OSError)`。coding bug（KeyError/TypeError/AttributeError）现在会正确冒泡。
- `enrich_papers.py:470`
- 外层 `gather(return_exceptions=True)` 已经兜底，内层这一层让 KeyError 等真 bug 只剩一行 warning
- 修复方向：内层只 catch 网络 / 解析类，让 coding bug 抛出来

### ~~P2-11~~ ✅ `daily-papers-notes/SKILL.md:164` 用 `git add -A`

**已修（2026-05-22）**：改为 `git add "DailyPapers/" "论文笔记/" "概念库/"`，只暂存本次产出目录。
- 违反 git-safety 约定（可能暂存未跟踪敏感文件）。pin 到具体 path，跟 review skill 对齐

### ~~P2-12~~ ✅ `user-config.json` 有 `max_age_days / highlights_folder / compare_folder`，`DEFAULT_CONFIG` 没有

**已修（2026-05-22）**：`DEFAULT_CONFIG` 补齐 3 个缺失 key；新增 `highlights_dir()` / `compare_dir()` / `max_age_days()` 便捷函数。
- 各文件用 `.get(..., default)` 散落 fallback，schema 实际住两处
- 在 `user_config.py` 补 `highlights_dir() / compare_dir() / max_age_days()` 便捷函数

### ~~P2-13~~ ✅ 硬编码超时散落 6 个文件

**已修（2026-05-22）**：`DEFAULT_CONFIG` 加 `timeouts: {curl_html, curl_image, pdf_extract, arxiv_fetch}`。4 个脚本改为从 `timeouts_config()` 读取。`paper_daemon.py` 的 rate-limit wait 保持硬编码（语义不同，不是网络超时）。
- `fetch_and_score.py:200`、`enrich_papers.py:39/115/368`、`download_note_images.py:27/71/120/147`、`pdf_tools.py:121`、`paper_daemon.py:578`
- 修复方向：`user-config.json` 加 `timeouts:` 段

### ~~P2-14~~ ✅ `paper-reader/SKILL.md:352` 指向 `~/.claude/skills/_shared/user-config.json` 旧路径

**已修（2026-05-22）**：改为 `~/DailyPaper/skills/_shared/user-config.json`。
- spec #0 后真实路径是 `~/DailyPaper/skills/_shared/user-config.json`（symlink 让它仍能用）
- 文档需更新

### ~~P2-15~~ ✅ `paper-reader/SKILL.md:125` 跨 skill 用相对路径调子进程

**已修（2026-05-22）**：改为绝对路径 `~/DailyPaper/skills/daily-papers/download_note_images.py`。
- `python3 ../daily-papers/download_note_images.py`
- 脆弱。要么把脚本搬到 `_shared/`，要么文档注明这个耦合

### ~~P2-16~~ ✅ `backfill_links.py:147-178 update_diversion_table` 有死变量

**已修（pipeline 自动化 PR 中已清理）**：当前代码无 `old_pattern` / `new_text`，函数已重构为直接 `re.sub` on wikilinks。
- `old_pattern` / `new_text` 算了不用，实际 `re.sub`（line 171）用另一个 pattern
- 看着像没做完的重构

### ~~P2-17~~ ✅ `docs/superpowers/plans/` 同时存 `*.md` + `*-COMPLETION.md`

**已修（2026-05-21）**：删除 4 份已 ship spec 的源 plan 文件，只保留 `*-COMPLETION.md` 记录。
- 已 ship 的 spec 的源 plan 文件已无价值，留一份就够。考虑收尾时归档 plan，只保留 COMPLETION

### ~~P2-18~~ ✅ `test_pipeline_guard.py:48` 用了已废弃的 `tempfile.mktemp()`

**已修（2026-05-22）**：改为 `tempfile.mkstemp()` + `os.close(fd)`。
- TOCTOU 风险（测试场景影响低，但模式不该传播）
- 换 `tempfile.NamedTemporaryFile(delete=False)` 或 `tempfile.mkstemp()[1]`

### ~~P2-19~~ ✅ `test_fetch_no_trending.py` 是 7 个静态字符串断言

**已修（2026-05-22，由 P1-5 关闭）**：`test_merge_dedup.py` 提供了 10 个真正的行为测试覆盖 `fetch_and_score` 核心逻辑。`test_fetch_no_trending.py` 保留作为"永不引入 trending"的 tripwire。
- 都在查"字面量 'trending' 不出现"或"kwarg 被拒绝"
- 当"别再引入 HF Trending"的 tripwire 有效，但**完全没覆盖 `fetch_and_score` 的真实行为**
- 跟 P1-5 一起做

---

## P3 审计发现（polish / nice-to-have）

### ~~P3-1~~ ✅ `paper_daemon.py:53-57` 速率限制常量硬编码

**已修（2026-05-22）**：`DEFAULT_CONFIG` 新增 `rate_limits` 段（initial_wait / max_wait / wait_multiplier / between_papers_wait / quota_wait_time）；新增 `rate_limits_config()` 便捷函数；`paper_daemon.py` 改为从 config 读取。用户可通过 `user-config.json` 覆盖。

### ~~P3-2~~ ✅ `build_manifest.py` 硬编码 `/tmp/...`

**已修（2026-05-22）**：`--out` 默认值改为 `temp_file_path("library_import_manifest.json")`，走 `user_config` 的跨平台抽象。

### ~~P3-3~~ ✅ `extract_affiliations.py` 无测试

**已修（2026-05-22）**：新建 `scripts/test_extract_affiliations.py`，33 个测试覆盖 extract_header（3 场景）/ is_noise（7 场景）/ looks_like_sentence（4 场景）/ has_inst_keyword（4 场景含 word-boundary）/ clean_affiliation（4 场景）/ split_numbered_affiliations（3 场景）/ _is_author_line（4 场景）/ extract_affiliations integration（4 场景含 dedup/empty）。

### ~~P3-4~~ ✅ `paper_daemon.py` 子进程拉 `claude --dangerously-skip-permissions` 无信任模型注释

**已修（2026-05-22）**：加注释说明 paper_source 字段来自本地 Zotero DB（非外部输入），args 为 list 形式（无 shell 注入）。

### ~~P3-5~~ ✅ `build_manifest.py` 串行 for-loop 跑 PDF

**已修（2026-05-22）**：改为 `asyncio.gather + Semaphore(10)` 并发抽取，90 个 PDF I/O bound 场景预计 5-10× 提速。

### ~~P3-6~~ ✅ `update_history.py` 是 sync 但被 async review skill 通过 subprocess 调用

**已关闭（2026-05-22）**：`update_history()` 函数本身已是可 import 的纯 Python 函数。review skill 是 LLM 执行的 markdown 指令，必须走 subprocess 调用；开销可忽略（每次 run 只调一次）。无需修改。

### ~~P3-7~~ ✅ 3 个旧 test 用硬编码路径（新 test 已统一）

**已修（2026-05-22）**：3 个旧 test 统一改为 `Path(__file__).resolve().parents[1]`，docstring 中 `Run:` 路径也改为相对。全部 8 个 test 文件现在都是可移植路径。

### ~~P3-8~~ ✅ `test_pipeline_guard.py` 测试 fixture 缺

**已修（2026-05-22）**：新增 3 个边界用例 fixture + 测试：
- `draft_empty.md`：0 个 `### N.` 段 → pass（0 papers）
- `draft_malformed_triple.md`：不完整 Claim/Evidence/Confidence → C3 violation（triple_count=0）
- `enriched_no_url.json`：无 `url` 字段 → guard 不崩溃，跳过 C1 匹配

### ~~P3-9~~ ✅ `test_pdf_tools.py` cargo-cult `importlib.reload`

**已修（2026-05-22）**：移除 `importlib.reload` 调用和 `importlib.util` 未用导入。`pdf_tools` 通过 `import shutil` 引用 `shutil.which`，直接 patch `shutil.which` 即可生效无需 reload。

---

## 微清理（不开 spec，下次顺手做）

- [x] 删 `skills/_backup/hf-trending-removed-2026-05-20.md`（被 git 历史 + spec #1 完整覆盖）——已删除
- [x] 删 spec #2 review 提到的 2 处 dead `import subprocess`：（P1-3 同 PR 顺手完成）
  - ~~`skills/library-import/build_manifest.py:21`~~
  - ~~`skills/daily-papers/download_note_images.py:16`~~
- [x] `extract_text(input, ...)` 参数改名 `source`，避免遮蔽 Python 内置（spec #2 review 提）——已改，tests pass
- [x] `_check_binary` 错误信息改成跨平台（不只 `brew install poppler`）——已改为 macOS/Debian/Windows 三平台提示
- [x] 设 `git config --global user.email/name` 消掉 auto-attribution 警告——已设 yd11111 / 1784578480@qq.com
- [x] 确认 `skills/daily-papers/__pycache__/` 在 `.gitignore` 里（审计观察到目录存在）——已确认：根 `.gitignore` 含 `__pycache__/` 规则
- [x] 清理重构残留的 dead imports（P1-3/P2-4/P2-5 遗留）——已清理 6 处：
  - ~~`fetch_and_score.py` `import re` + `URLError`~~
  - ~~`build_manifest.py` `import re`~~
  - ~~`history_store.py` `from pathlib import Path`~~
  - ~~`backfill_links.py` `obsidian_vault_path`~~
  - ~~`user_config.py` `import os`~~

---

## 阻塞中（等外部条件）

- [x] **arxiv-live smoke**：2026-05-21 端到端跑通（15 篇抓取 + 15 篇富化 + 11 篇点评 + guard pass + vault 保存 + history 更新），spec #1/#2/#3 均验证通过
- [x] **spec #2 的 `extract_affiliations_pdf` 真实 arxiv smoke**：同上，9/15 篇获得 method_summary（PDF 提取正常工作）

---

## 备注

- "Hole closed" 列在每个 COMPLETION 末尾——这份 roadmap 不重复，去 `*-COMPLETION.md` 查
- audit 是 2026-05-21 一次性照片；半年后建议重做一次（新 spec 会引入新债，老债会自然消化）
- P1 / P2 / P3 是当下评估，不是固定身份——情况变化时随时调整
