---
name: paper-reader
description: |
  Use when user asks to "read paper", "analyze paper", "summarize paper",
  "读论文", "分析文献", "帮我看一下这篇paper", "论文笔记", or provides a PDF file
  that appears to be an academic paper. Specialized for audio / speech papers
  (TTS, ASR, Speech-LLM, Audio Codec, Full-duplex, Omni).

  Also supports Zotero integration: "读一下这篇论文 ...", "快速看一下这篇论文 ...",
  "批判性分析这篇论文 ...", "读一下 Zotero 里的 XXX"

  **重要触发词**: "读一下 XXX"、"读一下这篇"、"帮我读" → 必须调用此 skill
context: fork
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
---

> **开始前**: 先跟用户打个招呼 🐕

# 学术论文阅读助手 (Paper Reader)

专注音频/语音方向（TTS、ASR、Speech LLM、Codec、Vocoder、全双工、Omni），支持 Obsidian 笔记保存；Zotero 集成可选。

## Step 0: 读取共享配置

先读取 `~/DailyPaper/skills/_shared/user-config.json`，如果 `~/DailyPaper/skills/_shared/user-config.local.json` 存在，再用它覆盖默认值。

显式生成并在后续统一使用这些变量：

- `VAULT_PATH`
- `NOTES_PATH`
- `CONCEPTS_PATH`
- `ZOTERO_DB`
- `ZOTERO_STORAGE`
- `AUTO_REFRESH_INDEXES`
- `GIT_COMMIT_ENABLED`
- `GIT_PUSH_ENABLED`

其中：

- `NOTES_PATH = {VAULT_PATH}/{paper_notes_folder}`
- `CONCEPTS_PATH = {NOTES_PATH}/{concepts_folder}`
- `GIT_PUSH_ENABLED` 只有在 `GIT_COMMIT_ENABLED=true` 时才可能为真

后续统一使用上面的变量。

## Step 0.5: 激活领域知识（必做）

**在开始读任何论文前**，先 Read `references/audio-speech-terminology.md`，把音频/语音领域的术语词典、关键基线模型（VALL-E / Voicebox / CosyVoice / F5-TTS / Whisper / Moshi / EnCodec / DAC / HuBERT 等）、常见评测指标（MOS / UTMOS / WER / SIM-O / RTF / 首包延迟）装进上下文。

**如果用户用的是「批判性分析」模式**（触发词含「critique」「批判」「严格审」），**额外**再 Read `references/research_failure_modes.md`，把引用幻觉 5 类（Adams et al. 2026, arXiv:2602.05930）、TTS/全双工/ASR/Codec 各方向的领域红旗装进上下文。命中红旗的时候必须在 `## 局限与风险` section 显式点出来。

**所有模式都必须 Read** `references/no-hallucination-rules.md`，这是反幻觉的硬约束规范。**违反此规范的笔记产出无效**，需要重新生成。

这一步的目的是：
- 论文里出现 `RVQ`、`CFM`、`Duration Predictor`、`SECS` 等术语时，**不要当成新概念**重新解释，而是直接用专业理解
- 论文做对比时，**主动调用**这些基线名做有依据的判断，不要写"和现有方法对比"这种空话
- 写 `[[概念]]` 链接时，**遵循术语库里的命名规范**（如统一写 `[[EnCodec]]` 而非 `[[encodec]]`）

如果论文涉及 SVC / 音乐 / 声音事件检测等术语库未覆盖的细分方向，再 WebSearch 补充。

## 1. 接收论文

| 输入方式 | 示例 | 处理方法 |
|----------|------|----------|
| PDF 路径 | `/path/to/paper.pdf` | 直接 Read |
| arXiv 链接 | `https://arxiv.org/abs/xxxx` | WebFetch |
| Zotero 分类 | "VLA 分类的论文" | 查询数据库 → 列出 → 用户选择 |
| Zotero 搜索 | "Zotero 里的 π0.5" | 搜索标题 → 找到 PDF |
| 无 PDF | Zotero 条目无附件 | 从网上获取（见下方） |

### 无 PDF 时的获取流程

1. `python3 assets/zotero_helper.py info {item_id}` 获取论文信息
2. 按优先级获取：arXiv HTML > arXiv PDF > DOI > WebSearch 标题
3. 判断 arXiv ID：从 URL / Zotero extra 字段 / 标题搜索
4. 推荐直接 WebFetch `https://arxiv.org/html/{arxiv_id}`，无需下载
5. 跳过条件：既无 PDF 也无在线来源 / 非论文内容

> Zotero 详细操作见 `references/zotero-guide.md`

## 2. 阅读模式

| 模式 | 触发词 | 输出 |
|------|--------|------|
| **快速摘要** | "快速看一下"、"quick" | 3-5 句核心贡献 |
| **完整解析** | "详细分析"、默认 | 结构化笔记（用模板） |
| **批判分析** | "批判性分析"、"critique" | 方法论优缺点评估 |
| **知识提取** | "提取公式"、"技术细节" | 公式 + 算法伪代码 |

## 2.4 资源本地化（必做，§2.5 verify 的前置）

> 落地用户需求："PDF / HTML 图表 / GitHub 代码这些资源都可以单次获取后存储到本地。只是不用上传到 git。但是写材料都会用得到。后面要重新分析也用得到。"

### 2.4.1 一行命令搞定

```bash
python3 ~/DailyPaper/skills/_shared/cache_paper_resources.py {arxiv_id} \
    --github {github_url}     # 如有 GitHub repo URL；不传则跳过 clone
```

输出 JSON 到 stdout，含本地路径，**直接 copy 到论文笔记 frontmatter 的 cache 字段**：

| frontmatter 字段 | 值 | 说明 |
|---|---|---|
| `pdf_local` | `~/DailyPaper/.cache/papers/{arxiv_id}/paper.pdf` | vault 外，重型 |
| `html_local` | `~/DailyPaper/.cache/papers/{arxiv_id}/paper.html` | vault 外，离线 grep 用 |
| `figures_dir` | `_resources/{arxiv_id}/figures/` | vault 内**相对路径**，Obsidian wikilink 友好 |
| `github_local` | `~/DailyPaper/.cache/papers/{arxiv_id}/github/{org}_{repo}/` | vault 外，clone 完整 repo |
| `cached_at` | YYYY-MM-DD | 缓存日期 |

### 2.4.2 何时必须跑 §2.4

- ✅ 精读 / 完整解析 / 批判性分析 / dogfood 模式 → **强制**
- ✅ R6 知识地图联动需要做 §2.5 元数据 verify → **强制**（§2.5 必须基于本地缓存做）
- ⏭️ 快速摘要模式（"快速看一下"触发词）→ 可跳过，但建议至少下 PDF + HTML

### 2.4.3 缓存目录结构

```
~/DailyPaper/.cache/papers/{arxiv_id}/        ← vault 外，不进 git，长期持久
├── paper.pdf
├── paper.html
├── github/{org}_{repo}/                       ← default_clone_github=true 时自动 clone
└── meta.json                                  ← fetched_at + sources

vault/论文笔记/_resources/{arxiv_id}/         ← vault 内，加 .gitignore 排除，Obsidian 内嵌显示用
└── figures/
    ├── fig1_overview.png
    ├── fig2_arch.png
    └── ...
```

**为什么分两层**：
- 重型（PDF / HTML / GitHub clone）放 vault 外 → 不污染 vault，不让 Obsidian 索引
- 图表（轻型）放 vault 内 _resources/ → Obsidian 可以用 `![[_resources/{arxiv_id}/figures/fig1.png]]` wikilink 引用

### 2.4.4 笔记内引用图表

```md
![[_resources/{arxiv_id}/figures/fig1_overview.png]]
```

或（如某图必须用外链）：

```md
![Figure 1](https://arxiv.org/html/{arxiv_id}/.../fig1.png)
```

外链不可达时由 `download_note_images.py` 自动 fallback 到本地（保留现状机制）。

### 2.4.5 GitHub 代码读取

clone 后可以直接 Read：

```bash
ls ~/DailyPaper/.cache/papers/{arxiv_id}/github/{org}_{repo}/
grep -rn "_init_weights\|load_pretrained" ~/DailyPaper/.cache/papers/{arxiv_id}/github/ --include=*.py
```

§2.5 元数据 verify 的 GitHub 来源标注用相对路径（如 `[GitHub: modeling_qwen3_tts.py:L42]`，**不写完整本地绝对路径**——避免泄漏私有路径，详见 no-hallucination-rules.md §11.6）。

---

## 2.5 知识库元数据采集 + 三层 verify（必做，反幻觉硬约束）

> 本节落地用户洞察：「**应该在读论文同时就把更新知识库需要的信息从论文原文中确认好**」。
> 完整规范见 `references/no-hallucination-rules.md` §11 三层 verify。

### 2.5.1 为什么这一步必须做

论文笔记是论文原文的 5-10% 压缩。**任何延迟到下游 skill（paper-compare / 知识地图建设 / dogfood R6 / 周更 SOP）才做的 verify，都会因为"读笔记 ≠ 读原文"产生幻觉**（详见 [[方法论复盘-2026-05-26-知识地图建设]]）。

正确做法：**在 paper-reader 一次性 verify 所有"知识库下游需要"的具体技术断言**，写成 frontmatter 元数据 + §X 来源。下游 skill 直接消费已 verified 的元数据，不再做新断言。

### 2.5.2 必须 verify 的元数据清单（写入 frontmatter）

| 元数据维度 | verify 内容 | frontmatter 字段 |
|---|---|---|
| LM 参数初始化 | cold-start / warm-start (from X LLM) / scratch+warmup | `lm_init` |
| 训练 loss 设计 | speech-token only / 多任务 / 含文本 loss / KL 约束 / 多阶段 | `training_loss` |
| Tokenizer 架构 | text+speech 分离 / interleaved unified / 并行多 codebook | `tokenizer_arch` |
| 是否多任务训练 | true / false + 多任务 loss 权重 | `multitask` |
| 训练数据 | 具体小时数 + 语种比例 + 来源 | `training_data` |
| 后训练算法 | RLHF / DPO / DiffRO / 自定义 / 无 | `post_training` |
| Codec 内部细节（如适用）| RVQ N 层 / FSQ levels / 码本大小 / 帧率 | `codec_detail` |

每个字段值必须带来源标注：`[§3.2]` / `[Eq.5]` / `[Tab.2]` / `[Fig.3]` / `[GitHub: <repo>/<path>:<line>]`。

### 2.5.3 三层 verify 流程（强制顺序）

**Layer 1：论文原文**（首选）
- WebFetch arXiv HTML 全文 → 定位章节 / 公式 / 表格 / 图
- 标记 `[§3.2]` 类

**Layer 2：GitHub 源码**（论文原文不明时**必须**查）

**重要论文应该 clone 到本地**（详见 `references/no-hallucination-rules.md` §11.5）：

```bash
GITHUB_CACHE=/Users/xiangshu/DailyPaper/.cache/github
mkdir -p "$GITHUB_CACHE"
cd "$GITHUB_CACHE"
git clone --depth 1 https://github.com/<org>/<repo>.git <repo>
# 然后用 Read / grep / find 跨文件查找
```

本地化优势：跨文件 grep（如 `grep -rn "_init_weights"`）/ 看 git history / 离线访问。WebFetch 单文件难以替代。

**很多关键技术决策论文不写细节**，只能从代码看：

| 论文常见模糊处 | 必须查的代码路径 |
|---|---|
| "我们从 X 模型初始化" 但不说哪个 checkpoint | `init_weights()` / `load_pretrained()` / `model_init.py` / `pretrained_path` 配置 |
| "训练 loss 由 X 组成" 但不列公式 | `loss.py` / `trainer.py` / loss 函数定义处 |
| "我们用 RVQ codec" 但不说几层、码本大小 | `codec/config.yaml` / `model.py` 中 codec 实例化处 |
| "联合训练 ASR + TTS" 但不说 loss 权重 | `trainer.py` 中 multi-task loss aggregation |
| "用 X 数据集" 但不说 filtering 规则 | `data_pipeline/` / `dataset.py` |
| "我们用 RLHF" 但不说 reward / 算法细节 | `rlhf/` 或 `post_training/` 目录 |
| "双 tokenizer" 但不说内部架构 | `tokenizer/` 目录代码 + 配置 |

操作：
1. 论文 abstract / project page / footnote 找 GitHub repo 链接
2. WebFetch GitHub README 定位关键文件
3. WebFetch / Read 相关代码文件（`config.yaml` / `train.py` / `loss.py` / `tokenizer/` / `init_weights()` 等）
4. 标记 `[GitHub: <repo>/<path>:<line>]` 或 `[GitHub commit <SHA>]`

**反模式**：找到 GitHub 但只读 README，不读 trainer/loss 代码 = 等于没查源码。

**Layer 3：第三方实现 / 复现报告**（前两层都不够时）
- community 复现 / blog 解析
- 标 `[第三方: <URL>]`，或显式标"无可靠来源 verify，仅论文 abstract 描述"

### 2.5.4 如果论文未开源代码 + L1 不足

显式标 `lm_init: "L2 不可用（未开源），仅 L1 abstract 描述"`，并在笔记的"批判性思考-可复现性"段提示。**不要**基于通用直觉脑补。

### 2.5.5 与 R6 / R7 的协作关系

- R6（知识地图联动）：基于 §2.5 verified 的元数据填 🗺️/🔄 区块，**禁止**脑补
- R7（反幻觉零容忍）：所有具体技术断言强制三档分级 + 三层 verify 来源
- §2.5 的 verified 元数据是 R6/R7 的事实基础

---

## 3. 笔记生成

**模板**: 严格遵循 `assets/paper-note-template.md`，不可自行简化。

### 核心质量规则

1. **零遗漏**: 论文中所有 Figure、所有公式、所有 Table 必须全部出现在笔记中
2. **内联概念链接**: 正文中首次出现的技术术语必须用 `[[概念]]` 链接，不仅仅是结尾
3. **严禁 ASCII 流程图**: 用结构化 Markdown 列表 + `$数学符号$` 描述架构
4. **公式完整性**: 每个公式必须有名称（`[[概念|名称]]`）、LaTeX 公式、含义、符号说明
5. **图片外链优先**: arXiv HTML / 项目主页 / GitHub，找不到再本地下载

### 学术严谨性规则（必读）

精读笔记要接近"reviewer 式精读"，不是"组会宣传稿"。以下规则与核心质量规则同等重要：

#### R1: 分离 Paper Claim 与 My Assessment

对论文核心结论，必须区分"作者说了什么"和"我判断它是否成立"。

- 原文说 "achieves SOTA" → 不要直接写"刷新SOTA"
- 正确写法：`**Paper Claim**: ... | **My Assessment**: 在作者报告的设置下表现领先，但 {具体限定条件}`
- 在"批判性思考"段中，每个核心 claim 都要有这对标记

#### R2: 禁用绝对化措辞

以下词汇**禁止**在笔记中出现（用右侧替代）：

| 禁用 | 替代 |
|------|------|
| 碾压 | 明显优于 / 整体占优 |
| 全面领先 | 在所报告评测中领先 |
| 全面超越 | 在多项指标上优于 |
| 绝对 SOTA | 当前报告结果中最优 |
| 真正 work 了 | 显示出可行性 |
| 革命性 / 突破性 | 显著改进 / 重要进展 |
| 首次实现 | 据作者称首次实现（需看全文确认） |

#### R3: 结果可信度分层

在"实验"段末尾，必须加一个"结果可信度"小节，将论文结果分三档：

- **高可信**: 有完整公开 benchmark、与强基线公平对比、可复现
- **中可信**: 有数据但评测设置不完全透明、基线选择有疑问
- **低可信**: 主观评测 / baseline 不透明 / 缺显著性检验 / 仅内部数据

#### R4: 方法横向定位

在"方法详解"段的开头，必须有 2-3 句话把论文放到领域图谱里：
- 与哪类范式最像（如"属于 codec LM 路线，与 VALL-E / SPEAR-TTS 同类"）
- 核心 novelty 相对已有工作在哪（不是复述 contribution，而是定位差异）

#### R5: 追问 Why

方法段不只复述"做了什么"，还要解释：
- 为什么这样设计有效（作者给的理由 + 你的判断）
- 与已有工作的同类设计有什么本质区别
- 如果作者没解释 why，显式标注"论文未解释此设计选择的动机"

#### R7: 反幻觉零容忍（最高优先级）

涉及单篇论文**具体技术决策**的断言（LM 初始化策略 / loss 设计 / tokenizer 架构 / 多任务训练 / 关键 ablation / 数据规模等，详见 `references/no-hallucination-rules.md` §1），**必须**采用三档分级前置标记：

| 档位 | 前置标记 | 何时用 |
|---|---|---|
| ✅ 已 verify | `[已 verify §X]` 或 `[已 verify GitHub commit/file]` | 读了论文该章节原文或代码 |
| ⚠️ 基于笔记摘要 | `[未 verify，仅笔记摘要]` | 引用现有论文笔记的浓缩 |
| ⚠️ 通用直觉 | `[未 verify，ML 直觉推断]` | 极少使用，必须配合 propose verify |

**强拒答模式**：当前会话**没有 WebFetch 该论文 HTML 也没读过其笔记**时，**禁止**做"X 是 Y"式的具体技术决策断言，必须改为"未读全文 + propose 先读 §X"。

**特别警告 — 优雅陷阱**：当开始构造"X vs Y vs Z"整齐三方对比表时**最容易产生幻觉**。看到自己想画对比表时先停一下问："每个 cell 我都 verify 过吗？" 没全 verify → 拆成独立 bullet，不要画整齐对照表。

**二阶判断特别要求（R6 配套）**：🗺️ 在知识地图中的定位 + 🔄 后续重估两个区块里的具体技术对照判断（如"X 是 cold start，Y 是 warm start"）必须分级标注；没 verify 的写为"待 verify"+ 追加到 [[待回填地图]] 的 verify 任务，不要假装已 verify。

详细规则与 9 节自检清单见 `references/no-hallucination-rules.md`。

**触发场景示例**（必须用三档分级或拒答模式）：
- "X 模型用 warm start 训练" → 必须 verify 论文 §训练流程或 GitHub trainer 代码
- "Y 模型的 codec 是 RVQ 8 层" → 必须 verify 论文 §codec 或代码 codec config
- "Z 模型在 LibriSpeech WER < 3%" → 必须 verify 论文 §实验表格

**触发场景反例**（不需要分级，属高层定位 / 主观判断）：
- "这是 LLM-native TTS 路线代表"（高层定位）
- "我认为这个设计可能受限于 X"（明示主观）
- "Mimi 是流式 codec"（领域常识）

#### R6: 知识地图联动（必填）

每篇论文笔记必须能回答"它会更新哪张地图"——这是从论文库升级到知识系统的关键约束。

**两个动作**：

**(1) frontmatter 必填以下字段**（标准定义见 `{NOTES_PATH}/0-工作台/笔记frontmatter规范.md`）：

| 字段 | 含义 | 示例 |
|---|---|---|
| `domain` | 一级领域，单选 | `TTS` / `ASR` / `Codec` / `SpeechLM` / `Dialogue` |
| `routes` | 技术路线，多选 | `[codec-lm-tts, instruction-tts]` |
| `problems` | 解决/触及的核心问题 | `[zero-shot-cloning, evaluation]` |
| `representations` | 涉及的表示空间 | `[acoustic-token, mixed-token]` |
| `related_maps` | 应反哺哪些地图（最少 1 个）| `["[[TTS-技术路线图]]", "[[TTS-表示层地图]]"]` |
| `evidence_level` | 证据强度 | `high` / `medium` / `low` |
| `maturity` | 技术路线成熟度 | `mature` / `emerging` / `exploratory` |
| `last_repositioned` | 最近一次基于新认知重新定位的日期 | `YYYY-MM-DD` |

**枚举值参考**（不要凭印象自创新枚举值）：
- 必读 `{NOTES_PATH}/0-工作台/笔记frontmatter规范.md` §2-§4 获取最新枚举
- 如果文件不存在或论文不属于已定义枚举（如新方向 SVS），可以 fallback 到自定义但要在 routes / problems 末尾加 `, "其他: <自定义>"`

**重要警惕**（Position #11 / Azzuni 2025 警示）：
- `evidence_level=high` 的门槛很高 —— 需要独立第三方评测验证 + 开源可复现。多数 2024-2026 论文应保守标 `medium`
- `maturity` 不等于"知名度" —— VALL-E 系列虽广泛使用但 codec 设计未收敛，仍标 `emerging`

**(2) 正文必有两个固定区块**（模板已含，不可省略）：

```md
## 🗺️ 在知识地图中的定位
- **所属领域**：[[{domain}-领域总览]]
- **技术路线**：[[{domain}-技术路线图]] §<具体章节>
- **核心问题**：[[{domain}-核心挑战]] §<挑战名>
- **表示层位置**：[[{domain}-表示层地图]] §<表示类型>（如适用）
- **在 SpeechLM/对话框架内的位置**：[[TTS-SpeechLM-Dialogue关系]] 位置 ① / ② / ③ / ④（如适用）
- **相邻工作**：[[{相邻模型}]] / ...

## 🔄 后续重估
- **{date}**：初读。{你的初步判断 + 限定条件}
```

> 公式/图片/表格的详细质量规范见 `references/quality-standards.md`

### 图片获取流程（多源 fallback）

**目标**: 确保笔记中包含论文的**所有 Figure**，先统计论文 Figure 总数再逐一获取。

1. WebSearch `"{论文标题} arxiv"` 获取 arXiv ID
2. **来源 A — arXiv HTML**（首选）：
   - WebFetch `https://arxiv.org/html/{arxiv_id}` 提取所有 `<figure>` 的标题与 img src URL
   - 统计论文 Figure 总数，确认提取数量是否完整
3. **来源 B — 项目主页**（HTML 404 或图片不全时）：
   - 从摘要/HTML 中查找项目主页 URL（常见模式：`project page`、`github.io`、`our website`）
   - WebFetch 项目主页，提取展示图片（通常包含 teaser / demo 图）
4. **来源 C — PDF 提取**（前两者都失败时）：
   - 调 `_shared/pdf_tools.extract_images(pdf_path, out_dir, prefix, min_size_bytes=10240)`（spec #2 集中化封装），返回 >= 10 KB 的图片 Path 列表。不要直接 shell out `pdfimages`
5. 笔记中用 `![Figure X](url)` 外链嵌入
6. 验证：外链可加载 / 本地文件 >10KB
7. **URL 去重**：写入前检查 URL 中是否有重复的 arxiv_id 路径段（如 `2603.05312v1/2603.05312v1/`），有则删除重复段。详见 `references/image-troubleshooting.md`

> ar5iv 编号不一定对应 Figure 编号，排错见 `references/image-troubleshooting.md`

### 图片可靠性保障（生成后自动执行）

笔记保存后，运行图片可达性检查脚本，自动将不可访问的外链图片下载到本地：
```bash
python3 ~/DailyPaper/skills/daily-papers/download_note_images.py "{笔记完整路径}"
```
- 可达的外链保持不动，不可达的自动下载到 `assets/` 并替换为 Obsidian wikilink
- 如有本地化操作，frontmatter `image_source` 自动更新为 `mixed`

### 公式格式

每个公式必须包含：名称（`[[概念|名称]]`）、LaTeX `$$` 块（前后留空行）、含义、符号列表。
`$$` 块前后**必须有空行**否则 Obsidian 不渲染。超长公式用 `aligned` 拆分。

## 4. Obsidian 保存

### 文件命名

只用**方法名/模型名**：`{方法名}.md`（如 `Pi05.md`，不加年份前缀）。
方法名判断：标题冒号前 / Abstract 中 "We propose XXX" / 希腊字母转 ASCII。
不确定时保存到 `_待整理/`。

### 保存路径

**铁律：必须落到 `references/concept-categories.md` 表中列出的 15 个预设子目录之一**（`1-TTS与语音合成` / `2-ASR与语音识别` / `3-Audio-Codec与Tokenizer` / `4-Vocoder与声码器` / `5-Speech-LLM与AudioLM` / `6-全双工与对话` / `7-Omni与多模态` / `8-Diffusion与FlowMatching` / `9-语音SSL与表示` / `10-语音翻译与跨语言` / `11-韵律与情感` / `12-数据集与评测` / `13-训练方法与对齐` / `14-LLM基础` / `15-其他音频任务`）。

**绝对禁止**自己发明顶层目录名（如 `Speech-LLM/`、`Duplex/`、`TTS/` 这类）。如果论文跨多个分类，按**最主要的论文贡献维度**选一个；多模态全双工模型应优先看是「Omni 突破」还是「Duplex 突破」决定。

如果用户配置了 Zotero（`ZOTERO_DB` 非空且文件存在），可叠加 Zotero collection 作为路径前缀；否则直接用：

`{NOTES_PATH}/{预设分类目录}/{方法名}.md`

### YAML frontmatter

完整模板见 `assets/paper-note-template.md`。简化示例（**注意**：含知识地图联动字段，不可省略）：

```yaml
---
title: "论文标题"
method_name: "MethodName"
authors: [Author1, Author2]
year: 2025
venue: arXiv
arxiv_id: "2412.06602"
tags: [tag1, tag2]                     # 小写连字符，3-8 个
zotero_collection: ...

# === 知识地图联动（R6 强制要求）===
domain: TTS
routes: [codec-lm-tts, instruction-tts]
problems: [zero-shot-cloning, evaluation]
representations: [acoustic-token]
related_maps:
  - "[[TTS-技术路线图]]"
  - "[[TTS-评测体系]]"
evidence_level: medium
maturity: emerging
last_repositioned: YYYY-MM-DD

# === 回流状态 ===
map_backfilled: false
backfilled_at:

image_source: online
created: YYYY-MM-DD
---
```

Tags 判断：看 Related Work 小标题 + Abstract 关键词。第一个 tag 是最核心主题。
知识地图联动字段判断：见上方 R6 + `{NOTES_PATH}/0-工作台/笔记frontmatter规范.md`。

### 保存后自动执行

1. **追加到待回填地图**（R6 配套动作，防御性）：

   先检查 `{NOTES_PATH}/0-工作台/待回填地图.md` 是否存在。**不存在则跳过**（不要报错，不要新建文件）。

   如存在，用 Edit 在 `# 待处理条目` 段下追加一条新记录。位置：找到最新日期的 `## YYYY-MM-DD` 锚点（如今天的）。如果今天日期还没有锚点，在 `# 待处理条目` 行之后新增一个 `## YYYY-MM-DD` 节。

   条目模板：

   ```md
   ### [[{方法名}]]
   - **domain**: {domain}
   - **routes**: {routes 逗号分隔}
   - **problems**: {problems 逗号分隔}
   - **representations**: {representations 逗号分隔}
   - **建议回填到**：
     - [[{related_map1}]] —— {一句话说补什么}
     - [[{related_map2}]] —— {一句话说补什么}
   - **状态**: 待处理
   ```

   `建议回填到` 的内容直接复用 frontmatter 的 `related_maps`，再加一句"补什么"的提示语（不要长，10-20 字即可）。

2. 只有在 `AUTO_REFRESH_INDEXES=true` 时才刷新目录页：
   ```bash
   python3 ../_shared/generate_concept_mocs.py
   python3 ../_shared/generate_paper_mocs.py
   ```
3. 只有在 `GIT_COMMIT_ENABLED=true` 时才做 git：
   - 先确认 `VAULT_PATH/.git` 存在
   - `git add {新增文件} {paper_notes_folder}/` 后必须真的有 staged changes
   - 满足条件后再执行：
   ```bash
   cd {VAULT_PATH} && git add {新增文件} {paper_notes_folder}/ && git commit -m "add paper note: {方法名}"
   ```
   - 只有在 `GIT_PUSH_ENABLED=true` 且仓库已配置远端时才 push

## 5. 概念库维护（每篇论文必做）

概念库位置：`{CONCEPTS_PATH}`

### 流程

1. **扫描**论文笔记中所有 `[[概念]]` 链接
2. **检查**每个链接对应的概念笔记是否存在（`ls` + `find`）
3. **创建**不存在的概念（不可跳过），自动归类到对应子目录

> 分类规则和模板见 `references/concept-categories.md`

### 自检

- [ ] 笔记中所有 `[[概念]]` 链接的概念笔记都存在？
- [ ] 概念笔记包含本论文作为"代表工作"？

## 6. 完成后自检（合并 checklist）

- [ ] 所有 Figure 都在笔记中（数量与论文一致）？
- [ ] 所有公式都在笔记中（变量一致、无冲突）？
- [ ] 所有 Table 完整保留（所有行列）？
- [ ] 正文中技术术语有 `[[概念]]` 内联链接？
- [ ] 概念库已更新（缺失的概念已创建）？
- [ ] 图片可用（外链可加载 / 本地 >10KB）？
- [ ] **R6 知识地图联动**：frontmatter 含 `domain` / `routes` / `problems` / `representations` / `related_maps` / `evidence_level` / `maturity` / `last_repositioned` 全部字段？
- [ ] **R6 知识地图联动**：正文含「🗺️ 在知识地图中的定位」「🔄 后续重估」两个区块？
- [ ] **R6 知识地图联动**：已追加条目到 `0-工作台/待回填地图.md`（若文件存在）？
- [ ] **R7 反幻觉**：所有具体技术决策断言（LM 初始化 / loss / tokenizer 架构 / 多任务 / ablation / 数据规模等）都带 `[已 verify §X]` / `[未 verify，仅笔记摘要]` / `[未 verify，ML 直觉推断]` 三档前置标记？
- [ ] **R7 反幻觉**：是否画了"X vs Y vs Z"整齐对照表？如有，每个 cell 都已 verify 吗？未 verify 的拆成独立 bullet 了吗？
- [ ] **R7 反幻觉**：当前会话有 WebFetch 该论文 HTML 吗？没有的话 🗺️/🔄 区块是否仅用了"已读笔记"档而非"已 verify §X"档？
- [ ] **R7 反幻觉**：是否有任何无标记的"X 是 Y"式断言遗漏？

## 7. 交互式功能

完成解析后询问：深入解释？对比其他论文？保存到 Obsidian？
保存后自动创建缺失概念笔记，报告新增概念数量。

## 8. 批量处理

支持 Zotero 分类批量处理（默认递归子分类）。流程：递归获取论文 → 去重 → 跳过已有笔记 → 依次处理 → 汇总。

## 参考文件（按需查阅）

- **`references/zotero-guide.md`** — Zotero 查询、分类、PDF 路径获取、智能分类判断
- **`references/image-troubleshooting.md`** — ar5iv 图片编号对应、PDF 提取备选
- **`references/concept-categories.md`** — 概念自动归类的 16 个子目录规则 + 模板
- **`references/quality-standards.md`** — 公式/图片/表格的详细质量规范 + 自检清单
