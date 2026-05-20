---
name: paper-highlights
description: |
  Use when the user wants to extract design highlights / innovations from a paper
  and accumulate them into a long-running "innovation library" organized by topic.

  Triggers (中英): "抽取亮点"、"记一下创新点"、"方案亮点入库"、"这篇有什么值得学的"、
  "把 [[X]] 的亮点入库"、"highlights from [[X]]"

  Input: an existing Obsidian paper note ([[wikilink]]) OR a new paper (URL/PDF).
  If new, will call paper-reader first.

  Output: appends 3-6 highlight entries to topic files under
  {VAULT_PATH}/论文笔记/_创新亮点/{topic}.md. Each entry is timestamped and back-linked
  to the source paper note.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch
---

> **开始前**: 先说一句 "开始抽取亮点 💡" 并报出处理的论文。

# 创新点抽取与入库 (Paper Highlights)

把一篇论文的方案亮点拆成 3-6 条「可借鉴的设计/思路」，按主题追加到长期累积的「创新点库」。

## Step 0: 读取共享配置

读取 `../_shared/user-config.json`，显式生成：

- `VAULT_PATH`
- `NOTES_PATH = {VAULT_PATH}/{paper_notes_folder}`
- `HIGHLIGHTS_PATH = {NOTES_PATH}/{highlights_folder}`（默认 `_创新亮点`）
- `AUTO_REFRESH_INDEXES`

若 `paths.highlights_folder` 不在配置里，回退到 `_创新亮点`。

## Step 1: 拿到论文笔记

| 输入形态 | 处理 |
|---|---|
| `[[NoteName]]` | Glob `{NOTES_PATH}/**/NoteName.md`；Read 笔记 |
| arXiv URL / PDF | 先调用 paper-reader 生成完整笔记，再回到本流程 |
| 标题/方法名模糊 | Glob 模糊匹配，多个命中让用户选 |

## Step 2: 抽取 3-6 个亮点

仔细读完笔记后，归纳出**真正有创新或值得借鉴**的设计点。**铁律**：

- 不要把"用了 Transformer"、"用了 RVQ" 这种业界标准操作当亮点
- 不要重复论文 abstract 的卖点措辞，要用**结构化复述**
- 每个亮点必须能回答：「我把这个搬到我的系统里能解决什么问题？」
- 同一篇论文的亮点不要重复。如果论文真的只有 1-2 个亮点，就只写 1-2 个，不要凑数
- 如果通篇没有可借鉴的创新（彻底灌水），如实告知用户，**不入库**

每个亮点用下面结构写：

```markdown
### 💡 {一句话亮点标题（动词开头）}
**来源**: [[源笔记名]] · {YYYY-MM-DD 抽取}

**技术原理**（2-3 句话）：
{这个亮点具体是怎么做的}

**为什么 work**（动机/直觉/避免了什么问题）：
{把作者的设计动机讲清楚}

**可借鉴方向**：
- 迁到 {场景A} 可以解决 ...
- 替换 {组件B} 时可以参考 ...

**相关概念**: [[Flow Matching]] [[Duration Predictor]] [[RVQ]]
```

## Step 3: 分类入库

每个亮点选一个**主题文件**追加到 `{HIGHLIGHTS_PATH}/{topic}.md`。预设主题文件名：

| 主题文件 | 收什么 |
|---|---|
| `Codec设计.md` | 码本结构、码率/质量权衡、低层 token 设计 |
| `Tokenizer设计.md` | 语义/声学 token、frame rate、量化方式 |
| `推理加速.md` | 蒸馏、剪枝、KV cache、并行解码、NFE 优化 |
| `流式与低延迟.md` | chunk 流式、首包延迟、look-ahead 控制 |
| `对齐与时长建模.md` | duration predictor、forced alignment、隐式对齐 |
| `表达性与韵律.md` | prosody encoder、情感、风格控制、自然性 |
| `数据合成与增广.md` | 数据 pipeline、伪标签、数据清洗、规模扩展 |
| `多语种与跨语言.md` | code-switch、跨语种迁移、多语种 phoneme |
| `全双工与中断处理.md` | turn-taking、barge-in、双流建模、VAD-free |
| `Speech-LLM架构.md` | speech-in/out、统一 backbone、token 流设计 |
| `训练范式.md` | DPO/RLHF for speech、curriculum、distillation |
| `评测方法.md` | 新评测集、新指标、自动评测器 |
| `Vocoder与重建.md` | 声码器设计、Mel→Wav、单阶段端到端 |

不在表里的主题：先想能不能并到现有文件；实在不行 → `_待分类.md`。**不要为单条亮点新开主题文件**，除非确实需要。

### 入库格式

每个主题文件结构（首次创建时初始化，后续追加）：

```markdown
---
type: highlights-collection
topic: {主题名}
tags: [highlights, paper-highlights]
---

# {主题名} · 创新亮点合集

> 跨论文累积的可借鉴设计点。每条带来源 + 抽取日期，按时间倒序排列（最新在上）。

---

{追加的亮点条目按 ### 💡 顺序往上插}
```

**追加方式**：
1. Read 现有主题文件（不存在则用模板创建）
2. 把新亮点条目插在 `---\n\n` 分隔符**之后**、已有条目之前（最新在上）
3. 用 Write 覆盖整文件（因为我们做了完整重排）

## Step 4: 反向链接到源论文笔记

在源论文笔记末尾追加（如果还没追加过）：

```markdown

> 💡 **已入库亮点** ({YYYY-MM-DD})：[[Codec设计]] · [[流式与低延迟]]
```

用 `[[主题文件名]]` 链接到主题合集。先 Read 笔记确认未存在同日链接，避免重复。

## Step 5: 刷新索引（可选）

`AUTO_REFRESH_INDEXES=true` 时跑：

```bash
python3 ../_shared/generate_paper_mocs.py
```

## 输出

完成后告知用户：
- 从 {论文名} 抽出了 N 个亮点
- 分别入库到哪些主题文件（列出）
- 是否在源笔记里追加了反向链接

## 注意事项

- **质量 > 数量**：宁可只写 2 条扎实的亮点，也不要凑 6 条水的
- **基于事实**：亮点必须在笔记里有直接出处。不要把笔记里没说的"读者推测"写进去
- **可借鉴方向要具体**：不要写"可以用在很多场景"，要写到具体任务/组件
- **不要重复**：每次入库前 grep 一遍同主题文件，避免和已有条目重复
