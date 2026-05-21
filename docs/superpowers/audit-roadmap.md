# DailyPaper Audit Roadmap

> 集中追踪所有"该做但还没做"的事。每个 spec 完成后回来打勾 / 补条目；
> 新 spec 开工前先扫一眼这里有没有更高优的事被压住。

- **建立日期**：2026-05-21（spec #2 收尾时一次性整理）
- **来源**：4 份 `*-COMPLETION.md` 的 "Pending follow-ups" + 一次完整代码审计
- **维护方式**：完成一条就标 `[x]` 并写"由 spec #N 关闭"，不要删；累积形成历史

---

## 已完成的 spec

- [x] **spec #0** — repo 重构：git init 外层 + skills 从 `~/.claude/` 迁到 `~/DailyPaper/skills/` 经 symlink
- [x] **spec #1** — 砍掉 HF Trending 抓取（只留 HF Daily + arxiv）
- [x] **spec #2** — `_shared/pdf_tools.py` 集中封装 + 3 caller 迁移（关闭 audit P1-1）
- [x] **spec #3** — `pipeline_guard.py` 把对抗式自查从 prose 升到代码（关闭 audit P1-2）

---

## 进行中 / 已规划的 spec

- [ ] **spec #4 — Semantic Scholar / OpenAlex DOI 富化**
  - 跨源主键（arxiv id 之外用 DOI 拉 affiliations / citations）
  - 多个 COMPLETION 都点名了；spec #2 的 `pdf_tools.extract_text(doi_url, first_n_pages=2)` 为它预留好了
  - **状态**：未开始；下个开工的 spec 候选

- [ ] **spec #5（暂定）— library-import 重构**
  - 修 `.pdf.md` 空文件 bug
  - 修 SKILL.md Step 3.3 自相矛盾的 figure 处理流程（写了 `/tmp/library_figs` 但没脚本生成）
  - 顺便用 `pdf_tools.extract_images` 做 figure fallback
  - **状态**：未开始；优先级中

- [ ] **future「domain research」skill**
  - 把 spec #1 删掉的 HF Trending 抓取从 `_backup/` 复活，做"领域定向调研"
  - **状态**：等有需求再做，本身就被延期

---

## P1 审计发现（latent bug / 安全 / 静默错乱，必做）

### P1-3：`extract_arxiv_id` 重复实现 6 次且有一处 regex 偏弱
- **位置**：
  - `skills/daily-papers/fetch_and_score.py:283-285` → `r"(\d{4}\.\d{4,5})"`
  - `skills/daily-papers/download_note_images.py:54-57` → 同上
  - `skills/daily-papers/enrich_papers.py:392-393` → 同上（inline）
  - `skills/daily-papers-review/update_history.py:58-61` → `r'arxiv\.org/abs/(\d+\.\d+)'` ⚠️ **更宽松**，会匹配 `arxiv.org/abs/1.2`
  - `skills/_shared/pipeline_guard.py:32` → `r"arxiv\.org/abs/(\d{4}\.\d{4,5})"`
  - `skills/library-import/build_manifest.py:31` → `r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b"`（唯一处理 `v\d+` 的）
- **影响**：`update_history.py` 的弱 regex 会把 `arxiv.org/abs/1.2` 这种 garbage 写进 `.history.json` 污染 dedup；每加一个 caller 又抄一份
- **修复方向**：抽 `_shared/arxiv_id.py`：`extract_id(url) / extract_all_ids(text)`，统一支持 `vN` 后缀剥离

### P1-4：`enrich_papers.py` HTML 抽取 zero unit tests（584 行）
- **位置**：`skills/daily-papers/enrich_papers.py:131-312`
- **影响**：`extract_figure_url / extract_authors_html / extract_affiliations_html / extract_method_summary` 都是 regex；arxiv / HF 改 HTML 时静默退化为空 enrichment，pipeline 继续跑，用户只能凭"今天报告里没图"才发现
- **修复方向**：fixture 一批 HTML 片段 + 5-8 个 parser 测试

### P1-5：`fetch_and_score.merge_and_dedup` zero unit tests
- **位置**：`skills/daily-papers/fetch_and_score.py:312-446`
- **影响**：「只抓真新论文」的核心逻辑——age filter / history dedup / min score / backfill。一次回归就会静默放老论文进去（5-19 incident 就是这样发生的）
- **修复方向**：fixture papers 数组 + 5-10 个 dedup 场景测试

### P1-6：`library-import/build_manifest.py` zero unit tests
- **位置**：整个文件
- **影响**：现状只有"用户跑没崩"算 pass；regex match / 重复名 / 缺 affiliations 等边界场景全靠肉眼
- **修复方向**：fixture 2-3 个 PDF（可重用 spec #2 的 sample.pdf）+ JSON 形状断言

### P1-7：`DEFAULT_CONFIG` 是旧机器人方向（与用户当前方向**相反**）
- **位置**：`skills/_shared/user_config.py:38-100`
- **影响**：fallback 关键词是 `world model / embodied ai / 3d gaussian splatting / cs.RO/cs.CV/cs.AI/cs.LG`，且 `negative_keywords` 包含 `speech synthesis / text-to-speech`——即"屏蔽用户真正想要的论文"。一旦 `user-config.json` 丢失或损坏，pipeline 会用反向偏好静默运行
- **修复方向**：两条路二选一——(a) 删除 keyword 部分让 missing config 直接报错，(b) 把默认值刷新为 TTS/speech 方向

### P1-8：`paper-reader/SKILL.md` 仍推荐直接 `pdfimages -png`
- **位置**：`skills/paper-reader/SKILL.md:114`
- **影响**：spec #2 已把 PDF 工具集中化，但 paper-reader 这份 prose 还在引导 LLM 直接 shell out。每次 LLM 读这份 SKILL 都会去 reinvent the wheel
- **修复方向**：改成"import `pdf_tools.extract_images` 通过子进程或 `python -c`"，或干脆删掉那段（让 LLM 自己探索）

### P1-9：`reorganize_notes.py` 是死代码且有**错误分类**
- **位置**：`skills/paper-reader/assets/reorganize_notes.py`（458 行）
- **影响**：`CATEGORY_RULES` 是旧的机器人 taxonomy（`3-机器人策略 / 4-足式运动 / 6-3D视觉`...）。当前 vault 是 speech taxonomy（`1-TTS与语音合成`...）。**如果有人误跑这个脚本，会把所有语音笔记打散到 `_待整理/`**
- **修复方向**：删（推荐）或为新 taxonomy 重写

---

## P2 审计发现（tech debt，应做）

### P2-1：`INST_KEYWORDS` 机构关键词列表重复
- `skills/daily-papers/enrich_papers.py:79-97` + `skills/daily-papers/extract_affiliations.py:16-38`
- 加一个学校要改两处。抽 `_shared/affiliation_keywords.py`

### P2-2：Zotero DB 辅助函数 3 处复制
- `paper-reader/paper_daemon.py` + `paper-reader/assets/zotero_helper.py` + `paper-reader/assets/reorganize_notes.py`
- 都是"开 readonly + 走 collections 树"。抽 `_shared/zotero_db.py`

### P2-3：`sys.path` bootstrap 在 10 个文件里 copy-paste
- 同样的 3 行 `_SHARED_DIR = ... / sys.path.insert(0, ...)` 出现 10 次
- 修复方向：(a) `_shared/` 加 `__init__.py` + `pyproject.toml` 当成包，或 (b) 一个 `_shared/bootstrap.py` 大家 import

### P2-4：`load_history` 实现 2 次，两个 schema owner
- `fetch_and_score.py:288-294` + `update_history.py:40-48,51-55`
- 一个常量叫 `HISTORY_PATH`、一个叫 `HISTORY_FILE`，指同一文件
- 抽 `_shared/history_store.py`：`load() / append(entries, date) / prune(days)`

### P2-5：method 名归一化逻辑分叉
- `paper_daemon.py:367-372` 处理下标 / 希腊字母 / `&→and` / 标点
- `backfill_links.py:46-47,105` 只 `.lower()`
- 后果：`π0.5.md` 在 paper_daemon 能匹配，在 backfill 永远匹配不上
- 抽 `_shared/method_name.py`

### P2-6：`paper-reader/paper_daemon.py` 无测试（788 行，最大文件）
- 至少这些纯函数该测：`title_matches_note / _normalize_method_name / _extract_note_method_names / parse_reset_wait_seconds / detect_limit_error`

### P2-7：`daily-papers-notes/backfill_links.py` 无测试
- `match_papers_with_notes`（line 80）regex 脆弱；`update_diversion_table` 不 match 时静默部分更新

### P2-8：错误处理无统一策略，9 处 silent return
- `enrich_papers.py:123,152,296`、`fetch_and_score.py:94`、`download_note_images.py:82,106,126,157`、`pdf_tools.py:43,45,60,66,69` 等
- 有的 print stderr 有的不，调用方区分不了"无数据" vs "binary 缺失 / crashed"
- 修复方向：引入 logging module + 统一 level（debug/info/warning/error）

### P2-9：`except (asyncio.TimeoutError, Exception)` 4 处冗余
- `Exception` 已经覆盖 `TimeoutError`，意图模糊
- 位置：`download_note_images.py:82,126,157`、`enrich_papers.py:119,375`
- 要么收窄（`OSError, SubprocessError`），要么直接 `except Exception`

### P2-10：`enrich_one` 内层 except 吞所有错（含 coding bug）
- `enrich_papers.py:470`
- 外层 `gather(return_exceptions=True)` 已经兜底，内层这一层让 KeyError 等真 bug 只剩一行 warning
- 修复方向：内层只 catch 网络 / 解析类，让 coding bug 抛出来

### P2-11：`daily-papers-notes/SKILL.md:164` 用 `git add -A`
- 违反 git-safety 约定（可能暂存未跟踪敏感文件）。pin 到具体 path，跟 review skill 对齐

### P2-12：`user-config.json` 有 `max_age_days / highlights_folder / compare_folder`，`DEFAULT_CONFIG` 没有
- 各文件用 `.get(..., default)` 散落 fallback，schema 实际住两处
- 在 `user_config.py` 补 `highlights_dir() / compare_dir() / max_age_days()` 便捷函数

### P2-13：硬编码超时散落 6 个文件
- `fetch_and_score.py:200`、`enrich_papers.py:39/115/368`、`download_note_images.py:27/71/120/147`、`pdf_tools.py:121`、`paper_daemon.py:578`
- 修复方向：`user-config.json` 加 `timeouts:` 段

### P2-14：`paper-reader/SKILL.md:352` 指向 `~/.claude/skills/_shared/user-config.json` 旧路径
- spec #0 后真实路径是 `~/DailyPaper/skills/_shared/user-config.json`（symlink 让它仍能用）
- 文档需更新

### P2-15：`paper-reader/SKILL.md:125` 跨 skill 用相对路径调子进程
- `python3 ../daily-papers/download_note_images.py`
- 脆弱。要么把脚本搬到 `_shared/`，要么文档注明这个耦合

### P2-16：`backfill_links.py:147-178 update_diversion_table` 有死变量
- `old_pattern` / `new_text` 算了不用，实际 `re.sub`（line 171）用另一个 pattern
- 看着像没做完的重构

### P2-17：`docs/superpowers/plans/` 同时存 `*.md` + `*-COMPLETION.md`
- 已 ship 的 spec 的源 plan 文件已无价值，留一份就够。考虑收尾时归档 plan，只保留 COMPLETION

### P2-18：`test_pipeline_guard.py:48` 用了已废弃的 `tempfile.mktemp()`
- TOCTOU 风险（测试场景影响低，但模式不该传播）
- 换 `tempfile.NamedTemporaryFile(delete=False)` 或 `tempfile.mkstemp()[1]`

### P2-19：`test_fetch_no_trending.py` 是 7 个静态字符串断言
- 都在查"字面量 'trending' 不出现"或"kwarg 被拒绝"
- 当"别再引入 HF Trending"的 tripwire 有效，但**完全没覆盖 `fetch_and_score` 的真实行为**
- 跟 P1-5 一起做

---

## P3 审计发现（polish / nice-to-have）

### P3-1：`paper_daemon.py:53-57` 速率限制常量硬编码
- `INITIAL_WAIT=60 / MAX_WAIT=21600 / QUOTA_WAIT_TIME=1800`
- 不同 Anthropic plan 用户可能想调

### P3-2：`build_manifest.py:48` 硬编码 `/tmp/...`
- 有 `_shared/user_config.py.temp_file_path()` 抽象但没用；Windows 下会挂

### P3-3：`extract_affiliations.py` 无测试
- 纯 regex pipeline，最适合 PDF-text fixture 单测

### P3-4：`paper_daemon.py:574` 子进程拉 `claude --dangerously-skip-permissions` 无信任模型注释
- 论文 `title / pdf_path` 字符串如果来源不可信，会被子 Claude 当指令读
- 不是注入风险（args 是 list 形），但建议加注释

### P3-5：`build_manifest.py` 串行 for-loop 跑 PDF
- 90 个 PDF I/O bound，能用 `asyncio.gather + Semaphore(10)` 提速 5-10×

### P3-6：`update_history.py` 是 sync 但被 async review skill 通过 subprocess 调用
- pipeline 已经付 subprocess 开销。未来重构：让它可 import，review 直接调用

### P3-7：3 个 test 用 3 种不同方式找 skills 路径
- `test_pdf_tools.py:17`、`test_pipeline_guard.py:17` → 硬编码 `/Users/xiangshu/DailyPaper`
- `test_fetch_no_trending.py:18` → `Path.home() / ".claude" / "skills"`（靠 symlink）
- 统一到 `Path(__file__).resolve().parents[1]`

### P3-8：`test_pipeline_guard.py` 测试 fixture 缺
- 空 draft（0 个 `### N.` 段）
- malformed `Claim/Evidence/Confidence` 行
- enriched.json 无 `url` 字段（应该 safe 但没 fixture）
- `--json-out` 失败时是否被新数据覆盖

### P3-9：`test_pdf_tools.py:85-107 test_binary_missing_raises` 用了 cargo-cult `importlib.reload`
- 简化：直接 monkey-patch `pdf_tools._check_binary` 或用 `unittest.mock.patch("pdf_tools.shutil.which")`
- （已记录在 spec #2 minor items，此处只是 cross-reference）

---

## 微清理（不开 spec，下次顺手做）

- [ ] 删 `skills/_backup/hf-trending-removed-2026-05-20.md`（被 git 历史 + spec #1 完整覆盖）
- [ ] 删 spec #2 review 提到的 2 处 dead `import subprocess`：
  - `skills/library-import/build_manifest.py:21`
  - `skills/daily-papers/download_note_images.py:16`
- [ ] `extract_text(input, ...)` 参数改名 `source`，避免遮蔽 Python 内置（spec #2 review 提）
- [ ] `_check_binary` 错误信息改成跨平台（不只 `brew install poppler`）
- [ ] 设 `git config --global user.email/name` 消掉 auto-attribution 警告
- [ ] 确认 `skills/daily-papers/__pycache__/` 在 `.gitignore` 里（审计观察到目录存在）

---

## 阻塞中（等外部条件）

- [ ] **arxiv-live smoke**：spec #1 / #2 / #3 都依赖一次真实 `今日论文推荐` 跑通来端到端验证。arxiv 429 限流清就自动验证
- [ ] **spec #2 的 `extract_affiliations_pdf` 真实 arxiv smoke**：同上

---

## 备注

- "Hole closed" 列在每个 COMPLETION 末尾——这份 roadmap 不重复，去 `*-COMPLETION.md` 查
- audit 是 2026-05-21 一次性照片；半年后建议重做一次（新 spec 会引入新债，老债会自然消化）
- P1 / P2 / P3 是当下评估，不是固定身份——情况变化时随时调整
