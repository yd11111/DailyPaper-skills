---
name: daily-papers-weekly
description: |
  Weekly meta-digest of the past 7 days of daily paper recommendations.
  Aggregates daily reports + newly added paper notes + newly added highlights,
  then asks Claude to synthesize cross-day trends, themes, and standout work.

  Triggers (中英): "本周论文总结"、"周报"、"weekly digest"、"过去一周综述"、
  "过去 7 天总结"。

  Output: {VAULT_PATH}/DailyPapers/Weekly/YYYY-WW.md (ISO week number).
---

> **开始前**: 先说 "开始本周综述 📊" + 报本周 ISO 编号 + 覆盖日期范围。

# 本周论文综述 (Weekly Digest)

把过去 7 天每天的零散推荐 / 必读 / 概念抽取 / 高亮，**跨日做横向总结**，产出一张能让用户 5 分钟看完一周进展的纸。

## Step 0: 读取共享配置

读 `../_shared/user-config.json`，显式生成：

- `VAULT_PATH`
- `DAILY_PAPERS_PATH = {VAULT_PATH}/{daily_papers_folder}` (默认 `DailyPapers`)
- `NOTES_PATH = {VAULT_PATH}/{paper_notes_folder}`
- `HIGHLIGHTS_PATH = {NOTES_PATH}/{highlights_folder}` (默认 `_创新亮点`)
- `WEEKLY_PATH = {DAILY_PAPERS_PATH}/Weekly`（不存在则 mkdir）
- `AUTO_REFRESH_INDEXES` / `GIT_COMMIT_ENABLED` / `GIT_PUSH_ENABLED`

## Step 1: 计算日期窗口

- `today` = 今天日期
- 默认覆盖窗口：`[today - 6 days, today]` 共 7 天（含今天）
- ISO 周编号：`YYYY-WW`（Python `date.isocalendar()` 得 `(year, week, weekday)`，年取 `iso_year`，周取 `iso_week` 两位补零）
- 输出文件：`{WEEKLY_PATH}/{iso_year}-W{iso_week:02d}.md`（如 `2026-W20.md`）

如果文件已存在 → 覆盖（每次都重算最新一周）。

## Step 2: 收集本周原料

### 2.1 daily 报告
Glob `{DAILY_PAPERS_PATH}/YYYY-MM-DD-论文推荐.md`，过滤日期落在窗口内的文件，按日期升序排列。**逐个 Read**。

如果窗口内 0 篇 → 写一个极简文件说"本周无推荐报告（系统未运行或被排除日）"，结束。

### 2.2 新增笔记
扫描 `{NOTES_PATH}/` 下所有论文笔记（排除 `_` 开头目录的"_概念/_创新亮点/_对比报告/_待整理"），`stat` 拿到 mtime，过滤 mtime 在本周窗口内的。把它们的文件名 + frontmatter 关键字段（method_name / tags / venue / zotero_collection）抽出来作为"本周必读清单"。

### 2.3 新增概念
扫描 `{NOTES_PATH}/_概念/**/*.md`，过滤本周创建（mtime 在窗口内），统计每个分类下新增了几个、列出名称。

### 2.4 新增创新亮点
扫描 `{HIGHLIGHTS_PATH}/*.md`，按 mtime 过滤。提取本周新追加的亮点条目（每个亮点在主题文件里以 `### 💡 ...` 开头）。

## Step 3: 跨日 meta 综合

把上面四类原料拼好后，按下面结构生成周报。**人设和 daily-papers-review 一致——毒舌但有依据的资深审稿人**，但视角拉到一周尺度。

### 输出结构

```markdown
---
type: weekly-digest
iso_week: YYYY-WW
date_from: YYYY-MM-DD
date_to: YYYY-MM-DD
days_covered: N
tags: [weekly-digest, auto-generated]
---

# 📊 第 WW 周综述（YYYY-MM-DD ~ YYYY-MM-DD）

## ⚡ 一句话

{本周 TTS / Audio 圈子在卷什么；最值得读的 1-2 篇；哪些方向在爆发；哪些是水翻天。3 句话，结尾要有判断}

## 📈 数字

| 维度 | 本周 | 备注 |
|---|---|---|
| 推荐论文（去重） | N | 含 daily 跨天去重后的口径 |
| 🔥 必读 | N | 笔记已生成 |
| 👀 值得看 | N | |
| 💤 可跳过 | N | |
| 新增概念笔记 | N | |
| 新增亮点条目 | N | |
| 跑通天数 | N / 7 | 没跑的日期列出 |

## 🎯 本周必读速览（带链接）

按方向分组，每篇一行：

### TTS / 语音合成
- [[VibeVoice]] · M-D · 一句话亮点
- ...

### 全双工 / 对话
- [[OmniFlatten]] · M-D · ...

### Omni / 多模态
- [[MiniCPM-o-4.5]] · M-D · ...

### Codec / Tokenizer / Vocoder
- ...

### ASR
- ...

### Speech LLM / Audio LM
- ...

### 其他
- ...

（没新增的方向直接省略段落，不要空列表）

## 🔥 一周方向小评（按方向给一句"卷得怎么样"）

### TTS
- {对比本周 TTS 几篇的趋势：是大家都在卷 codec 压缩？还是在卷流式？是 Flow Matching 一统天下还是 AR/NAR 并立？}
- {点名跨论文的撞车 / 互补关系}

### 全双工 / Omni
- ...

### ASR & 其他
- ...

## 💡 本周新增亮点（按主题）

按 _创新亮点/ 目录列举本周新增的亮点条目（每条用短形式）：

### Codec设计
- 💡 {亮点标题} ← [[源笔记]]
- ...

### 流式与低延迟
- ...

## 🧠 新概念观察

把本周新增到 _概念/ 的概念**只挑前 10 个最值得记的**列出来，用一句话评价"为什么需要知道这个"：

- [[Mimi]]: Kyutai 12.5 Hz 超低码率 codec，专为 LLM 设计；做端到端 speech LLM 时几乎必读
- [[Flow Matching]]: ...
- ...

> 全量在 _概念/ 目录下能看到。

## 🚦 趋势判断 + 下周关注什么

{2-3 句话。明确表达态度。例如："TTS 的 codec 压缩这条路已经接近极限，下周可以多盯 evaluation 改进的工作"、"全双工还在范式期，等 Moshi 之后的下一篇真 SOTA"。}

## 📅 附：本周覆盖的 daily 报告

- [[YYYY-MM-DD-论文推荐]] · N 篇
- [[YYYY-MM-DD-论文推荐]] · N 篇
- ...
```

### 写作铁律

- **跨日撞车**优先点出：如果两篇论文在不同日子都解决了类似问题，直接对比"谁更狠"
- **不要复述每篇细节**：daily 报告已经写过了，周报的价值是 meta 综合
- **数字必须能在原始 daily 报告里查到**——不要瞎编
- **没新增的方向**写"本周空白"，不要硬凑
- **亮点条目去重**：如果同一篇笔记产生了多个亮点，按主题分别列即可；不要把所有亮点堆在一起
- **方向小评至少 1 行评价**：不能只列论文不评

## Step 4: 保存 + Git

写到 `{WEEKLY_PATH}/{iso_year}-W{iso_week:02d}.md`（不存在的 `Weekly/` 子目录先 `mkdir -p`）。

仅当 `GIT_COMMIT_ENABLED=true` 时：

```bash
cd {VAULT_PATH} && git add "{daily_papers_folder}/Weekly/" && git commit -m "weekly digest: {iso_year}-W{iso_week}"
```

仅当 `GIT_PUSH_ENABLED=true` 时 `git push`。

## Step 5: 刷新 MOC（可选）

`AUTO_REFRESH_INDEXES=true` 时：

```bash
python3 ../_shared/generate_paper_mocs.py
```

注：MOC 默认不会扫 DailyPapers 子目录，但保险起见跑一下。

## 输出

完成后告知用户：
- 周报文件路径
- 本周必读 N 篇 / 新概念 N 个 / 新亮点 N 条
- 一句话本周判断
