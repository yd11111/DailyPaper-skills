---
name: paper-compare
description: |
  Use when the user wants to compare 2+ audio/speech papers and produce a structured
  comparison report with a matrix, distinct highlights, similarities, and a verdict on
  which paper fits which use case.

  Triggers (中英): "对比一下"、"比较一下 X 跟 Y"、"X vs Y"、"compare these papers"、
  "把 [[A]] 跟 [[B]] 比一下"、"跟 [[已有笔记]] 做对比"

  Input can be a mix of: (a) Obsidian wikilinks like [[CosyVoice]] (existing notes),
  (b) arXiv URLs / PDFs (will trigger paper-reader first), (c) paper titles to search.

  Output: a comparison report saved to {VAULT_PATH}/论文笔记/_对比报告/.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch
---

> **开始前**: 先说一句 "开始对比 🔍" 并列出本次对比的论文清单。

# 论文对比助手 (Paper Compare)

为音频/语音方向的论文做结构化对比，产出可执行的「该读谁/该用哪个」判断。

## Step 0: 读取共享配置

读取 `../_shared/user-config.json`（local 覆盖默认），显式生成：

- `VAULT_PATH`
- `NOTES_PATH = {VAULT_PATH}/{paper_notes_folder}`
- `CONCEPTS_PATH = {NOTES_PATH}/{concepts_folder}`
- `COMPARE_PATH = {NOTES_PATH}/{compare_folder}`（默认 `_对比报告`）
- `AUTO_REFRESH_INDEXES`

如果 `paths.compare_folder` 在配置中不存在，回退到字面值 `_对比报告`。

## Step 0.5: 激活领域知识

Read `../paper-reader/references/audio-speech-terminology.md`，加载基线模型清单和评测指标，使对比表能直接引用 VALL-E / Voicebox / CosyVoice 等基线对应位次。

## Step 1: 解析输入

把用户输入解析成 N 个论文对象。每个对象一定要先解析到一个**本地笔记路径**：

| 输入形态 | 处理方法 |
|---|---|
| `[[NoteName]]` | Glob `{NOTES_PATH}/**/NoteName.md`；找不到 → 报错请用户确认 |
| arXiv URL / abs / PDF / HTML | 调用 paper-reader 生成笔记后再回到本流程 |
| 标题或方法名 | Glob 模糊匹配 `{NOTES_PATH}/**/*关键词*.md`；多个命中让用户挑 |

若用户给了 2 个以上 wikilink 但其中一个本地不存在，先告知用户并询问：是否先调用 paper-reader 生成？或换一篇？**不擅自跳过**。

## Step 2: 抽取结构化卡片

对每篇论文，从笔记中（或新生成的笔记中）抽取下列字段。**不在笔记里的信息不要编**，写 "未提及"。

```yaml
title: ...
method_name: ...
year: 2024
venue: arXiv / Interspeech / ICASSP / ...
task: TTS / ASR / Speech-LLM / Codec / Vocoder / Duplex / Omni / ...
paradigm: AR / NAR / Flow Matching / Diffusion / Hybrid / RVQ-LM
input: text / phoneme / waveform / mel / token / speech-prompt
output: waveform / mel / discrete token / text
audio_representation: waveform / mel(80) / EnCodec-token / SemanticToken+AcousticToken / ...
training_data: LibriTTS / LibriHeavy / Emilia / Seed / 自建 / ...（含规模）
key_components: [组件1, 组件2, ...]   # 如 [Flow Matching, X-Codec, Phi-3 backbone]
baselines: [VALL-E, Voicebox, CosyVoice, ...]
streaming: yes / no / partial
latency: 首包/RTF/端到端，数字 + 单位
metrics:
  MOS: ...
  UTMOS: ...
  WER: ...
  SIM-O: ...
  RTF: ...
open_source: code/model/data 各自有无
limitations: [...]
```

## Step 3: 写对比报告

保存到 `{COMPARE_PATH}/YYYY-MM-DD-{A}-vs-{B}[-vs-{C}].md`。文件结构：

```markdown
---
type: compare
date: YYYY-MM-DD
papers: ["[[A]]", "[[B]]", ...]
tags: [paper-compare, auto-generated]
---

# {A} vs {B} vs ... 对比

## 一句话结论
{每篇一句话定位 + 我应该读哪个的判断}

## 速览矩阵

| 维度 | [[A]] | [[B]] | [[C]] |
|---|---|---|---|
| 任务 | TTS | TTS | Speech-LLM |
| 范式 | NAR + Flow | AR + Codec | AR Discrete |
| 输入→输出 | text→wav | text+prompt→token | text/audio→audio |
| 音频表示 | Mel + Vocos | EnCodec 8RVQ | Mimi 1.1kbps |
| 训练数据 | LibriTTS 585h | Emilia 100kh | 自建 7M h |
| 流式 | ✅ | ❌ | ✅ |
| 延迟/RTF | 0.05 RTF | 0.3 RTF | 160 ms 首包 |
| MOS / UTMOS | 4.3 / 4.05 | 4.4 / 4.10 | 4.1 / 3.9 |
| WER (Whisper-large) | 2.1% | 2.3% | 3.5% |
| SIM-O | 0.68 | 0.71 | 0.55 |
| 开源 | code+ckpt | code | code+ckpt+data |

> 表格里**只填论文中明确报告的数字**，未报告写 "—"。不同论文如果用了不同 ASR/Speaker Encoder 算的，加 ⚠️ 注脚说明可比性弱。

## 相同点 / 共同范式
- ...
- ...

## 关键差异
1. **{维度1}**: A 用 X 路线，B 用 Y 路线，原因 / 后果是 ...
2. ...

## 各自的亮点（值得借鉴）
### [[A]]
- 亮点 1 + 为什么 work
- ...

### [[B]]
- ...

## 各自的硬伤
- ...

## 该选谁 / 该读谁
- 想做**零样本 TTS 落地**：选 {X}，原因 ...
- 想研究 **codec 设计**：去看 {Y} 的 ablation
- 不要做 **{某场景}**：{Z} 不适合，原因 ...

## 关联概念
- [[Flow Matching]]、[[RVQ]]、[[Speech-LLM]] ...
```

## Step 4: 反向链接（可选）

在每篇被对比的论文笔记末尾追加（如果还没有同名链接的话）：

```markdown

> 🔍 **对比报告**: [[YYYY-MM-DD-{A}-vs-{B}]]
```

用 Edit / append 实现，**先 Read 笔记**确认是否已存在同链接，避免重复追加。

## Step 5: 刷新索引（可选）

仅当 `AUTO_REFRESH_INDEXES=true` 时执行：

```bash
python3 ../_shared/generate_paper_mocs.py
```

## 输出

完成后告知用户：
- 对比文件路径
- 主要结论一句话
- 关键差异 N 条
- 是否新生成了某些论文笔记（如有 paper-reader 调用）

## 注意事项

- **绝不编造数字**：所有评测数字必须能在论文/笔记里查到，找不到就写 "—" 或 "未报告"
- **同维度不同算法**：MOS / SIM-O / WER 的具体算法不同会让数字不可比，必须用脚注标出
- 至少 2 篇，最多建议 4 篇（>4 表格会过宽，可拆成多轮对比）
- 用户没明确选哪些维度时，按 Step 2 的全量字段对比；用户指定了维度（如「只比 codec 设计」）则聚焦那块
