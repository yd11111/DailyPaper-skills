# 论文核心技术判断的反幻觉规范

> 共享规范文件。任何涉及"对单篇论文做核心技术判断"的 skill（paper-reader / paper-compare / paper-highlights / daily-papers-review / daily-papers-notes）必须遵守。
>
> 触发的根本原因：2026-05-26 dogfood 时连续两次基于"通用 ML 直觉 + 笔记摘要"对 Qwen3-TTS 做了"unified-token-space" / "loss balancing" 等错误判断（详见 `~/.claude/projects/-Users-xiangshu-DailyPaper/memory/feedback_no_hallucination_on_paper_details.md`）。

---

## 1. 必须分级标注的断言范围

**任何涉及单篇论文具体技术决策的断言**都必须分级。所谓"具体技术决策"包括但不限于：

- **LM 参数初始化策略**：cold start（从头训练）vs warm start（用通用 LLM 初始化）vs scratch+warmup vs 多种 init 混合
- **训练 loss 设计**：有哪些 loss / 权重比例 / 是否多任务 / 是否含文本 loss / 是否 KL 约束
- **Tokenizer 架构**：text+speech 分离 vs interleaved 统一序列 vs 并行多 codebook vs unified-token-space
- **是否多任务训练**：单任务 / 多任务 / 多任务但分阶段 / 任务间是否共享参数
- **关键 ablation 选择**：哪些 ablation 真的做了 vs 论文只声称没实证
- **数据规模/构成**：具体小时数 / 配对方式 / 语种比例 / 数据来源
- **后训练算法选择**：RLHF / DPO / DiffRO / 自定义 reward
- **推理延迟/RTF/首包延迟**：声称的具体数值
- **零样本/克隆 SECS / WER 等评测数值**

**反例（幻觉源头）**：在没读论文相关章节的情况下，根据"看起来合理的 ML 直觉"或"过去类似工作的做法"做以下断言：
- "Qwen3-TTS 用 warm start 必须 loss balancing 防止 catastrophic forgetting"  ← 是直觉推断，论文实际没这个 loss
- "X 模型应该是 unified-token-space"  ← 把"用通用 LLM 初始化"误等同于"token 统一"
- "Y 模型在 LibriSpeech 上 WER < 3%"  ← 没核对原文表格就报具体数字

## 2. 三档分级体系

| 档位 | 强制前置标记 | 含义 | 何时使用 |
|---|---|---|---|
| ✅ **已 verify** | `[已 verify §X]` 或 `[已 verify GitHub commit/file]` | 读了论文该章节原文或代码 | 已 WebFetch arXiv HTML 全文该章节 / 已查 GitHub 代码 |
| ⚠️ **基于笔记摘要** | `[未 verify，仅笔记摘要]` | 引用现有论文笔记的浓缩，可能丢失原文细节 | 当前会话没读全文，但读过该论文笔记 |
| ⚠️ **通用直觉** | `[未 verify，ML 直觉推断]` | 没读论文也没读笔记，基于通用 ML 知识推断 | 极少使用——除非用户明确要求快速估计 |

**禁止**：写出**无任何分级标记**的具体技术断言。如果触发了 §1 范围又没标，必须重新生成。

## 3. 拒答模式（强制）

如果当前会话没有 WebFetch 该论文 HTML 也没读过其笔记，**禁止**做"X 是 Y / X 不是 Y"式的具体技术决策断言。

正确响应模板：

> 「**未读 [模型名] 论文全文，对 [具体技术问题] 我无法做可靠判断**。可能 X，但需要 verify 论文 §[相关章节] 才能确认。要我现在 WebFetch [arXiv ID] 的 §X 章节做 verify 吗？」

然后等用户拍板再行动。**绝对不要**直接抛出"基于通用直觉"的判断，再用警告标包装它——这本质上还是幻觉。

## 4. 优雅警告（元规则）

**当开始构造"X vs Y vs Z"三方分类对照表时，最容易产生幻觉**。

原因：
- "整齐的三方对比"是人脑的认知偏好（让叙述更结构化、好看）
- 但**整齐 ≠ 论文事实**
- 每个 cell 都对应一个具体技术断言，每个断言都需要独立 verify
- 一旦某 cell 是"为了对照美观"而填的（"Y 路线在该维度应该是 X"），就是幻觉

**应对策略**：
- 看到自己开始想画"3×3 整齐对比表"时，先停一下问："每个 cell 我都读过原文 verify 过吗？"
- 没全 verify → 不要画对照表，改为列每个模型独立的 bullet
- 已全 verify → 在表格下方列出每个 cell 的 verify 来源（论文 §X 或代码 commit）

## 5. 二阶判断（特别警告）

R6 中的 🗺️ 在知识地图中的定位 + 🔄 后续重估两个区块是**二阶判断**——基于论文笔记本身做的"它在更大框架里位于哪儿"的判断。这两块**最容易失真**，因为：

- 一阶笔记（核心方法 / 实验 / 结果）相对客观——基于论文原文复述
- 二阶判断（在哪条路线 / 与谁对照 / 趋势位置）需要"理解 + 比较"——容易脑补

**应对策略**：
- 二阶判断里的具体技术对照（如"X 是 cold start，Y 是 warm start"）必须使用本规范的三档分级
- 没 verify 的二阶判断写为"待 verify" + 在 [[待回填地图]] 中追加 verify 任务，不要假装已 verify

## 6. 不算"具体技术决策"的内容（不强制分级）

为避免规范扩散到所有文字，以下内容**不需要**分级标注：

- 论文整体定位的高层描述（如"这是 LLM-native TTS 路线代表"）
- 笔者主观判断（"我认为这个设计可能受限于 X" + 显式标"我的归纳"）
- 引用其他综述/笔记内容（已有的引用标注就够了）
- 已知的领域常识（如"Mimi 是流式 codec"）

**判定标准**：如果错了会让用户得到错误的工程结论，就需要分级；如果错了只是定位略偏，就不需要。

## 7. 自检清单（写完后必须过一遍）

在最终输出前，对以下问题逐一回答：

- [ ] 我做的每个**具体技术决策**断言都带 §2 的三档前置标记吗？
- [ ] 我画的对照表（如果有）是不是每个 cell 都已 verify？没全 verify 的拆成 bullet？
- [ ] 我写"X 是 Y / X 不是 Y"时，是基于读过的论文 §X 还是基于通用直觉？后者必须用拒答模式。
- [ ] R6 的 🗺️ + 🔄 两块里的具体对照判断，分级标了吗？
- [ ] 任何"基于 ML 直觉推断"的断言我都最好不写，写了必须明示 + propose verify 行动？

## 8. 与现有规则的关系

本规范与 paper-reader SKILL.md 中的 R1-R6 互补：

- **R1（区分 Paper Claim vs My Assessment）**：本规范进一步要求 My Assessment 也要分级（已 verify / 笔记摘要 / 直觉）
- **R2（禁绝对化措辞）**：本规范是 R2 的延伸——绝对化措辞往往伴随幻觉
- **R3（结果可信度分层）**：本规范的"档位"是 R3 的字段化版本
- **R5（追问 Why）**：本规范要求"Why" 解释里的具体细节也要 verify
- **R6（知识地图联动）**：本规范在 §5 特别警告 🗺️/🔄 二阶判断的幻觉风险

## 9. 适用 skill 清单

本规范应被以下 skill 通过 Step 0.5 加载：

- [x] `paper-reader/SKILL.md` — 写论文笔记时（首要适用）
- [ ] `paper-compare/SKILL.md` — 做对比报告时（特别强）
- [ ] `paper-highlights/SKILL.md` — 抽创新亮点时
- [ ] `daily-papers-review/SKILL.md` — 写日报锐评时
- [ ] `daily-papers-notes/SKILL.md` — 批量笔记时（通过调 paper-reader 间接生效）

未勾选的 skill 是后续应该补的扩散范围。

---

## 10. 二阶分析的特殊反幻觉规则（最高风险区）

### 10.1 核心原则

> **"读过论文笔记" ≠ "读过论文"**。论文笔记是**压缩版本**——精读笔记再详细也只是 5-10% 的原文信息。**任何基于已有笔记做的下游分析都建立在压缩信息上**，必然产生信息丢失型幻觉。

**二阶分析**定义：输入不是论文原文，而是已有论文笔记 / 已有综述 / 已有地图笔记，对它们做加工后的产出。包括：

- 元综述（基于多篇综述做综合）
- 知识地图（领域总览 / 技术路线图 / 模型谱系 / 核心挑战）
- 论文对比报告（paper-compare）
- 创新亮点抽取（paper-highlights）
- 趋势判断（基于多篇笔记 + 综述）
- R6 中的 🗺️/🔄 区块（基于论文笔记本身做框架级定位）
- 周更 SOP 中的"地图回填"（基于待回填条目修订地图）

### 10.2 为什么二阶分析最危险

**根本原因**：信息流是 `论文原文 → [压缩 1: 论文笔记] → [压缩 2: 综述/地图] → [压缩 3: 元综述/趋势]`。每一次压缩都丢信息，每一次基于压缩做断言都可能脑补缺失部分。

**典型幻觉模式**（按危险度递增）：

1. **复述偏差**：把笔记里的高层定位当作论文原文事实复述（"X 是 codec-LM 路线"是笔记里的归类，不一定是论文原文用词）
2. **类比脑补**：把通用 ML 直觉填进压缩版本的"看起来缺失但应该有"的位置（如"warm start 应该有 loss balancing"）
3. **整齐对照美化**：构造"X vs Y vs Z" 整齐对比表时填补 cell（dogfood 时的典型错误）
4. **趋势归纳错位**：把多篇笔记的高层定位整合成"趋势"，但每篇定位本身可能是上一次幻觉

### 10.3 强制规则

**规则 D1：所有二阶分析输出必须能溯源到原文**

- 每个具体技术断言必须直接引用论文原文 §X，**不能引用 "笔记里写了"**
- "笔记里写了 X" 不算 verify——笔记本身可能错
- 若只能引用笔记，必须用 `[未 verify，仅基于 [[笔记名]]]` 标注（不是 `[已 verify]`）

**规则 D2：知识地图笔记里的具体技术对照必须 §X verify**

- [[TTS-技术路线图]] 里的"X 路线代表是 Y" → Y 必须有论文 §verify
- [[TTS-代表模型谱系]] 里的"v1 → v2 → v3 演进改了什么" → 改了什么必须有论文 §verify
- [[TTS-核心挑战]] 挑战 X 下的"代表方案 Y" → Y 实际怎么做的必须有论文 §verify
- 没 verify 的 cell 必须明示"待 verify"

**规则 D3：dogfood / R6 补全必须读原文**

- 不能仅基于已有论文笔记做 R6 的 🗺️/🔄 区块
- 至少要 WebFetch 论文 arXiv HTML 的相关章节（方法 / 训练 / 实验）verify 笔记里的高层定位
- 没 WebFetch 就做的 R6 补全必须整体加 banner："本 🗺️/🔄 仅基于已有笔记，未读原文 verify，结论可能有偏差"

**规则 D4：paper-compare / paper-highlights 必须读原文**

- 这两类 skill 默认假设笔记够用 → 改为默认假设笔记不够用
- 任何对比表 / 亮点列表的具体技术 cell 必须 verify 论文原文，不能仅基于已有笔记
- 不读原文的对比 / 亮点必须明示警告

### 10.4 已有产出的处理

当发现一份产出（笔记、地图、对比报告）是仅基于二阶信息（笔记 + 笔记）做的：

1. **不要假装它已 verify** → 整体加"未 verify"banner
2. **逐 cell 重审** → 把每个具体技术断言拆出来，列入 [[待回填地图]] 的 verify 任务
3. **优先 verify 高影响 cell** → 影响地图判断、影响后续推荐的 cell 优先

### 10.5 自检追加（除 §7 外）

- [ ] 我的输入是论文原文还是已有笔记？
- [ ] 如果是已有笔记，我有没有把"笔记里写了 X"误当成"论文里写了 X"？
- [ ] 我的具体技术对照能引用论文 §X 吗？不能就该标"未 verify"
- [ ] 我画的对照表是不是为了 elegance 而把"应该是 X"写成"是 X"？
- [ ] 我是不是把多篇笔记的高层定位整合成"趋势"，但每篇定位都可能是上次幻觉？

---

## 11. 三层 verify 体系（论文原文 → GitHub → 第三方）

**verify 不是只读论文**。论文表述常常含糊（"我们用 X 方法"但不说细节），此时**必须查 GitHub 源码**。

### 11.1 三层 fallback

| Layer | 来源 | 何时用 | 标记格式 |
|---|---|---|---|
| **L1: 论文原文** | arXiv HTML / PDF | 首选，最快 | `[§3.2]` / `[Eq.5]` / `[Tab.2]` / `[Fig.3]` |
| **L2: GitHub 源码** | 论文公开的官方 repo | L1 含糊或不足时（**很常见**）| `[GitHub: <repo>/<path>:<line>]` 或 `[GitHub commit <SHA>]` |
| **L3: 第三方实现 / 复现报告** | community 复现、blog 解析 | 论文未开源 + L1 不足 | `[第三方: <URL>]` 或显式标"无可靠来源 verify" |

### 11.2 L2 GitHub 源码常见 verify 场景

很多关键技术决策**论文原文不写细节，只能从代码看**：

| 论文常见模糊处 | 必须查的代码路径 |
|---|---|
| "我们从 X 模型初始化" 但不说哪个 checkpoint | `init_weights()` / `load_pretrained()` / `model_init.py` / `pretrained_path` 配置 |
| "训练 loss 由 X 组成" 但不列公式 | `loss.py` / `trainer.py` / loss 函数定义处 |
| "我们用 RVQ codec" 但不说几层、码本大小 | `codec/config.yaml` / `model.py` 中 codec 实例化处 |
| "联合训练 ASR + TTS" 但不说 loss 权重 | `trainer.py` 中 multi-task loss aggregation |
| "用 X 数据集" 但不说具体 filtering 规则 | `data_pipeline/` / `dataset.py` |
| "我们用 RLHF" 但不说 reward / 算法细节 | `rlhf/` 或 `post_training/` 目录 |
| "双 tokenizer" 但不说内部架构 | `tokenizer/` 目录代码 + 配置 |

### 11.3 L2 不能 fallback 的情况

- **论文未开源代码** → 标"L2 不可用"，依赖 L1 + L3
- **代码与论文显著不一致** → **以代码为准**，但必须显式记录"代码 vs 论文不一致：论文说 X，代码做 Y"

### 11.4 实操建议（已被 §11.5 自动化，保留作为 fallback 行为说明）

paper-reader 读论文时，**默认行为**：

1. **跑 cache_paper_resources.py**（详见 §11.5 + paper-reader/SKILL.md §2.4）—— 一站式下载 PDF + HTML + GitHub clone + 提取图表
2. 之后所有 verify 直接读本地缓存（Read 命令、grep -rn）
3. 如果 §11.5 因网络/未开源等原因失败 → fallback 到 WebFetch（实时拉取，但不持久化）
4. 标注每个具体技术断言的 verify 来源

**反模式**：
- ❌ 论文说"用 RVQ codec"就直接写"RVQ"，不查 GitHub 看几层、码本大小
- ❌ 论文说"warm start"就直接写"warm start"，不查 GitHub 看具体从哪个 checkpoint
- ❌ 找到 GitHub 但只读 README，不读 trainer/loss 代码

### 11.5 本地化下载（自动化 helper：cache_paper_resources.py）

> **自动化方案已落地**：用 `_shared/cache_paper_resources.py` 一站式下载 PDF + HTML + 提取图表 + clone GitHub。涉及精读 / dogfood / 元洞察类的重要论文，**默认必跑** §11.5。

**为什么必须本地化**：

| 维度 | WebFetch 单文件 | 本地 clone / 下载 |
|---|---|---|
| 跨文件 grep | ❌ 必须事先猜文件名 | ✅ `grep -r "_init_weights" .` 一次找全 |
| 看 git history / blame | ❌ 不可能 | ✅ `git log --follow file` 能查设计来源 |
| 离线访问 | ❌ 每次依赖网络 | ✅ 任意 Read，速度快 |
| 结构化 PDF 读 | ⚠️ HTML 摘录可能丢图表 | ✅ PDF 工具精确读章节 / 表格 / 图 |
| 跨文件交叉引用 | ❌ 难 | ✅ 看 `import` 链能理解架构脉络 |

**自动化操作流程**（一行命令搞定全部）：

```bash
python3 ~/DailyPaper/skills/_shared/cache_paper_resources.py {arxiv_id} \
    --github https://github.com/<org>/<repo>
```

helper 自动完成：
- 下载 arXiv PDF → `~/DailyPaper/.cache/papers/{arxiv_id}/paper.pdf`
- 下载 arXiv HTML → `~/DailyPaper/.cache/papers/{arxiv_id}/paper.html`
- 提取 PDF 图表 → `vault/论文笔记/_resources/{arxiv_id}/figures/fig*.png`（vault 内，Obsidian wikilink 用）
- clone GitHub repo → `~/DailyPaper/.cache/papers/{arxiv_id}/github/{org}_{repo}/`（默认 `default_clone_github=true`）
- 写 meta.json 元数据
- 输出 JSON（含所有路径，可直接 copy 到论文笔记 frontmatter）

**为什么分 vault 外/内两层**：
- 重型（PDF / HTML / GitHub clone）→ vault 外 `~/DailyPaper/.cache/`：体积大，不让 Obsidian 索引，不进 git
- 图表（轻型）→ vault 内 `论文笔记/_resources/`（加 `.gitignore` 排除）：能用 `![[_resources/{arxiv_id}/figures/fig1.png]]` Obsidian wikilink 引用，跨设备 Obsidian sync 友好

**关键文件常用 grep（clone 后 5 类常用查询）**：
- `find . -name "*.yaml" -o -name "config*"` → 配置
- `grep -rn "_init_weights\|load_pretrained" --include=*.py` → 初始化
- `grep -rn "loss\s*=" --include=*.py` → loss 函数定义
- `find . -path "*/codec/*" -o -path "*/tokenizer/*"` → tokenizer 代码
- `find . -path "*/trainer*" -o -path "*/training*"` → 训练流程

**缓存管理**：`user-config.json` 的 `cache.retention_days`（默认 90 天）定义保留期。手动清理：
```bash
find ~/DailyPaper/.cache/papers -mindepth 1 -maxdepth 1 -mtime +90 -exec rm -rf {} \;
```

**何时不需要本地化**（可以仅 WebFetch fallback）：
- 快速读模式（"快速看一下" 触发词）
- 论文未开源代码 + arXiv 也无 PDF（极少）

**何时强制本地化**：
- 精读 / 批判性分析 模式
- dogfood / R6 补全 / 元洞察类二阶分析
- 重要工业系统（影响地图判断的代表性论文）

### 11.6 与 §2.4 / §2.5 的协作

- **§2.4 资源本地化**（paper-reader/SKILL.md）是 §2.5 的前置步骤——必须先跑 cache_paper_resources.py 才能做 verify
- §2.5 的"知识库元数据采集"中所有 [§X / GitHub: <path>] 标注都来自本地缓存，不再依赖网络
- frontmatter 的 `[GitHub: <path>]` 标注应该用**相对 repo 根的路径**（如 `[GitHub: modeling_qwen3_tts.py:L42]` 或 `[GitHub: cosyvoice3/loss.py:128]`），**不要写完整本地绝对路径**（如 `~/DailyPaper/.cache/.../...`），避免笔记泄漏私有路径
- 本地缓存路径全部由 `user-config.json` `cache` 段集中管理（`cache_root` / `papers_subdir` / `vault_resources_folder`）

### 11.7 user-config.json `cache` 段配置

```json
{
  "cache": {
    "cache_root": "~/DailyPaper/.cache",
    "papers_subdir": "papers",
    "vault_resources_folder": "_resources",
    "default_clone_github": true,
    "retention_days": 90
  }
}
```

通过 `_shared/user_config.py` 暴露的 helper：
- `cache_root()` → vault 外 cache 根目录
- `cache_papers_dir()` → cache/papers/
- `vault_resources_dir()` → vault 内 _resources/
- `default_clone_github()` → 默认是否 clone
- `cache_retention_days()` → 保留天数

### 11.5 三层 verify 的成本与收益

- **成本**：每篇论文多 5-15 分钟（找 repo + 读关键文件）
- **收益**：避免"论文摘要级理解"导致的幻觉链；让笔记成为可信赖的 ground truth
- **不做的代价**：所有下游二阶分析建立在不可靠的笔记上 → 幻觉随时间累积放大
