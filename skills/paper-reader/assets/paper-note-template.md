---
title: "{Title}"
method_name: "{MethodName}"
authors: [{Authors}]
year: {Year}
venue: {Venue}
arxiv_id: "{arxiv_id}"
tags: [{tags}]
zotero_collection: {zotero_path}

# === 论文核心技术元数据（三层 verify 强制要求，每条都标 [§X] / [GitHub: <path>] 来源）===
# 见 references/no-hallucination-rules.md §11 三层 verify 体系
# Layer 1: 论文原文 [§X / Eq.X / Tab.X / Fig.X]  → Layer 2: GitHub 源码 [GitHub: <repo>/<path>:<line>]  → Layer 3: 第三方实现
lm_init: "{描述} [§X 或 GitHub: <path>]"            # cold-start (从头训练) / warm-start (用 X LLM 初始化) / scratch+warmup
training_loss: "{描述} [§X / Eq.X / GitHub: <path>]" # speech-token CE only / 多任务 / 含文本 loss / KL 约束等
tokenizer_arch: "{描述} [§X / Fig.X / GitHub: <path>]" # text+speech 分离 / interleaved unified / 并行多 codebook 等
multitask: {true/false} "[§X 或 GitHub: <path>]"     # 是否多任务训练
training_data: "{规模 / 构成} [§X 或 GitHub: <path>]" # 具体小时数 + 语种比例 + 来源
post_training: "{算法} [§X 或 GitHub: <path>]"       # RLHF / DPO / DiffRO / 自定义 reward / 无
codec_detail: "{细节} [§X 或 GitHub: <path>]"        # RVQ N 层 / FSQ levels / 码本大小 / 帧率（如适用）

# === 知识地图联动（详见 0-工作台/笔记frontmatter规范）===
domain: {domain}                       # TTS / ASR / Codec / SpeechLM / Dialogue / Omni / SVS / ...
subdomain: {subdomain}                 # 可选，二级领域
routes: [{routes}]                     # 技术路线标签，多选，见规范 §2
problems: [{problems}]                 # 解决/触及的核心问题，多选，见规范 §3
representations: [{representations}]   # 涉及的表示空间，多选，见规范 §4
related_maps:                          # 应反哺哪些地图（最少 1 个）
  - "[[{map1}]]"
related_surveys:                       # 可选
  - "[[{survey1}]]"
evidence_level: {evidence}             # high / medium / low，见规范 §5
maturity: {maturity}                   # mature / emerging / exploratory，见规范 §6
last_repositioned: {date}              # 最近一次基于新认知重新定位的日期

# === 回流状态（由后续 review 人工/自动维护）===
map_backfilled: false                  # 是否已回填到地图
backfilled_at:                         # 回填完成时间

# === 资源本地化路径（cache_paper_resources.py 自动填充，详见 SKILL.md §2.4 + no-hallucination-rules.md §11.5）===
pdf_local: "{pdf_local_path}"          # vault 外 cache/papers/{arxiv_id}/paper.pdf
html_local: "{html_local_path}"        # vault 外 cache/papers/{arxiv_id}/paper.html（离线 grep 用）
figures_dir: "{figures_relative_path}" # vault 内 _resources/{arxiv_id}/figures/（Obsidian wikilink 用相对 paper_notes 路径）
github_local: "{github_local_path}"    # vault 外 cache/papers/{arxiv_id}/github/{org}_{repo}/（如 default_clone_github=true）
cached_at: {cached_at}                 # 资源缓存日期

# === 通用元数据 ===
image_source: online                   # online（默认）/ mixed / local
arxiv_html: {arxiv_html_url}           # 如有
created: {date}
---

# 论文笔记：{Title}

## 元信息

| 项目 | 内容 |
|------|------|
| 机构 | {Affiliations} |
| 日期 | {Month Year} |
| 项目主页 | {project_page_url} |
| 对比基线 | [[{baseline_paper}]] |
| 链接 | [arXiv]({arxiv_url}) / [Code]({code_url}) |

---

## 一句话总结

> {用一句话概括这篇论文的核心贡献，不超过50字}

---

## 核心贡献

1. **{贡献1标题}**: {简要说明}
2. **{贡献2标题}**: {简要说明}
3. **{贡献3标题}**: {简要说明}

---

## 问题背景

### 要解决的问题
{这篇论文要解决什么问题？}

### 现有方法的局限
{之前的方法有什么不足？}

### 本文的动机
{为什么作者认为他们的方法能解决这个问题？}

---

## 方法详解

### 领域定位

<!-- R4: 2-3 句话把论文放到领域图谱里 -->
{方法名} 属于 **{范式类别}** 路线（如 codec LM / flow matching / 端到端 VAE / 自回归 mel），与 [[{同类工作1}]]、[[{同类工作2}]] 同属一类。相对已有工作的核心差异在于 {一句话点明 novelty 定位}。

### 模型架构

<!-- 使用 [[概念]] 内联链接所有技术术语 -->

{方法名} 采用 **{架构类型}** 架构：
- **输入**: 语言指令 $l$ + 观测 $o_t$ + 状态 $s_t$
- **Backbone**: {使用的主干网络}
- **核心模块**: [[{核心技术1}]] 用于 [[{核心技术2}]]
- **输出**: [[Action Chunking|动作块]] $a_{t:t+k}$
- **总参数**: {参数量}

### 核心模块

#### 模块1: {名称}

**设计动机**: 利用 [[{相关概念}]] 实现 {目标}

**具体实现**:
- 使用 [[{技术A}]] 进行 {处理1}
- 通过 [[{技术B}]] 实现 {处理2}

#### 模块2: {名称}

{同上格式，注意内联概念链接}

---

## 关键公式

<!-- 公式标题使用 [[概念|名称]] 格式链接到概念库 -->

### 公式1: [[{概念名}|{公式用途}]]

$$
{公式内容}
$$

**含义**: {一句话解释公式的作用}

**符号说明**:
- $\tau \sim \mathcal{U}(0, 1)$: {含义}
- ${符号2}$: {含义}

### 公式2: [[{概念名}]] 损失

$$
\mathcal{L}_{total} = \lambda_1 \mathcal{L}_{task} + \lambda_2 \mathcal{L}_{reg}
$$

**含义**: {损失函数的整体作用}

**符号说明**:
- $\lambda_1, \lambda_2$: 权重系数
- $\mathcal{L}_{task}$: {任务损失作用}
- $\mathcal{L}_{reg}$: {正则项作用}

### 公式3: 采样/推理过程

$$
{推理公式}
$$

**含义**: {推理过程说明}

{... 列出论文中所有重要公式 ...}

---

## 关键图表

<!-- 图片：下载到本地 assets/ 文件夹，用 ![[]] wikilink 嵌入 -->
<!-- 命名规范: {方法名}_fig{N}_{英文描述}.png -->
<!-- 下载后必须验证：文件 >10KB、Read 确认内容正确 -->

### Figure 1: Overview / 系统概览

![[{MethodName}_fig1_overview.png]]

**说明**: {方法名} 的整体架构。输入 {输入内容}，通过 [[{核心技术}]] 处理，输出 {输出内容}。

### Figure 2: Model Architecture / 模型架构

![[{MethodName}_fig2_architecture.png]]

**说明**: 展示 [[{模块名}]] 的详细结构。{核心设计点}。

### Figure 3: Experiment Results / 实验结果

![[{MethodName}_fig3_results.png]]

**说明**: {实验的关键发现}，{方法名} 在 {指标} 上超越 baseline {百分比}。

### Table 1: {表格标题}

| Method | Metric1 | Metric2 | Metric3 |
|--------|---------|---------|---------|
| Baseline1 | x.xx | x.xx | x.xx |
| Baseline2 | x.xx | x.xx | x.xx |
| **Ours** | **x.xx** | **x.xx** | **x.xx** |

**说明**: {表格的关键发现}

### Table 2: 消融实验

| 配置 | Metric | 说明 |
|------|--------|------|
| w/o Module A | x.xx | {影响分析} |
| w/o Module B | x.xx | {影响分析} |
| Full Model | x.xx | - |

**关键发现**: {消融实验最重要的结论}

{... 列出论文中所有重要图表 ...}

---

## 实验

### 数据集

| 数据集 | 规模 | 特点 | 用途 |
|--------|------|------|------|
| {Dataset1} | {size} | {特点} | 训练/测试 |
| {Dataset2} | {size} | {特点} | 测试 |

### 实现细节

- **Backbone**: {使用的骨干网络}
- **优化器**: {Adam/SGD, 学习率}
- **Batch Size**: {大小}
- **训练轮数**: {epochs}
- **硬件**: {GPU 型号和数量}

### 可视化结果

{定性结果的关键观察}

### 结果可信度

<!-- R3: 将论文结果分三档 -->

| 可信度 | 结果 | 理由 |
|--------|------|------|
| **高** | {如: ASR 在 LibriSpeech 上的 WER} | {有标准 benchmark、强基线对比、可复现} |
| **中** | {如: TTS arena 胜率} | {主观评测、评审人数/显著性未给} |
| **低** | {如: Realtime 主观评分} | {baseline 不透明、量纲不明} |

---

## 批判性思考

### 核心 Claim 审查

<!-- R1: 区分 Paper Claim 和 My Assessment -->

1. **Paper Claim**: {作者的核心声明，如 "achieves SOTA on X"}
   **My Assessment**: {你的判断 + 依据，如 "在作者选取的 benchmark 上成立，但缺少与 Y 的对比"}

2. **Paper Claim**: {第二个核心声明}
   **My Assessment**: {判断}

### 优点
1. {优点1——具体指出哪个数字强、哪个设计有新意}
2. {优点2}
3. {优点3}

### 局限性
1. {局限1——具体指出哪个假设不成立、哪个实验缺了}
2. {局限2}

### 潜在改进方向
1. {改进方向1}
2. {改进方向2}

### 可复现性评估
- [ ] 代码开源
- [ ] 预训练模型
- [ ] 训练细节完整
- [ ] 数据集可获取

---

## 🗺️ 在知识地图中的定位

<!-- 必填。让每篇论文天然带"它会更新哪张地图"的信息。详见 0-工作台/笔记frontmatter规范 §7。 -->

- **所属领域**：[[{domain}-领域总览]]
- **技术路线**：[[{domain}-技术路线图]] §<具体路线/章节>
- **核心问题**：[[{domain}-核心挑战]] §<挑战名>
- **表示层位置**：[[{domain}-表示层地图]] §<表示类型>（如适用）
- **在 SpeechLM/对话框架内的位置**：[[TTS-SpeechLM-Dialogue关系]] 位置 ① / ② / ③ / ④（如适用）
- **相邻工作**：[[{相邻模型1}]] / [[{相邻模型2}]] / [[{相邻模型3}]]

---

## 🔄 后续重估

<!-- 每次基于新认知重新评估，加一行，不删旧条目。重估的演进本身就是知识。 -->

- **{date}**：初读。{你的初步判断 + 限定条件}

---

## 关联笔记

### 基于
- [[{前置工作1}]]: {说明}
- [[{前置工作2}]]: {说明}

### 对比
- [[{对比方法1}]]: {为什么对比}
- [[{对比方法2}]]: {为什么对比}

### 方法相关
- [[{核心技术1}]]: 核心方法
- [[{核心技术2}]]: 重要组件

### 硬件/数据相关
- [[{硬件或数据集}]]: {说明}

---

## 速查卡片

> [!summary] {Paper Title}
> - **核心**: {一句话核心}
> - **方法**: {关键方法}
> - **结果**: {主要结果}
> - **代码**: {GitHub链接}

---

*笔记创建时间: {timestamp}*
