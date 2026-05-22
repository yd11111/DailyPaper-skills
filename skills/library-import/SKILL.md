---
name: library-import
description: |
  One-shot import of a local PDF paper library into the Obsidian vault as
  Lite notes (1-3 KB each, NOT full deep notes). For ingesting an existing
  curated collection like the user's /Users/xiangshu/高德工作/文献 (~90 PDFs).

  Triggers (中英): "导入文献库 <路径>"、"library-import <path>"、
  "把 <路径> 这个 PDF 库导进 vault"。

  Designed for ONE-SHOT use; NOT for daily/repeat workflows.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

> **开始前**: 先说一句 "开始导入文献库 📚" + 报输入路径。

# 文献库一次性导入 (Library Import)

把用户本地已有的 PDF 论文库，**轻量化**导入 Obsidian vault，每篇生成 1-3 KB 的 Lite 笔记。

## 设计原则（不要破坏）

1. **Lite ≠ Full**：本 skill 不调用 paper-reader，不补概念库，不刷 MOC。**Python 层只做 metadata**，图的语义选择交给 Claude WebFetch（见 Step 3.0）
2. **复用现有 vault 结构**：所有笔记进 `论文笔记/{15 个预设分类}/{MethodName}.md`，frontmatter 加 `tags: [classic]` + `library_source` 标记
3. **PDF 一并归档**：原 PDF 复制到 `{VAULT_PATH}/assets/papers/{MethodName}.pdf`；笔记 frontmatter `pdf_path` 指向**它**（不是源路径），方便 vault 自洽
4. **批处理**：10 篇一批，避免单次上下文爆炸；每 30 篇做一次 git commit 阶段性保存
5. **失败不阻塞**：单篇出错（PDF 损坏、分类不准）写到 `_待整理/`，最后汇总报告，不中断

## Step 0: 读取共享配置

读 `../_shared/user-config.json`，显式生成：

- `VAULT_PATH`
- `NOTES_PATH = {VAULT_PATH}/{paper_notes_folder}`
- `ASSETS_PATH = {VAULT_PATH}/assets/papers`（不存在则 `mkdir -p`）
- `GIT_COMMIT_ENABLED` / `GIT_PUSH_ENABLED`

## Step 1: 构建 manifest

如果用户给了路径（默认就是 `/Users/xiangshu/高德工作/文献`），先跑：

```bash
python3 ~/DailyPaper/skills/library-import/build_manifest.py "<library_root>"
```

manifest 落在 `/tmp/library_import_manifest.json`，含每篇 PDF 的：

```json
{
  "filename": "VibeVoice.pdf",
  "absolute_path": "/Users/xiangshu/高德工作/文献/TTS-LLM/VibeVoice.pdf",
  "relative_path": "TTS-LLM/VibeVoice.pdf",
  "source_topic": "TTS-LLM",
  "first_page_text": "V IBE VOICE Technical Report\n\nThis report ...",
  "first_page_chars": 6000,
  "arxiv_id": "2508.19205" 或 null,
  "file_size_bytes": 1234567
}
```

跑完用 Read 工具读 manifest，确认总数和主题分布合理。

## Step 2: 主题映射 → vault 15 分类

`source_topic` 是用户手工分类，**作为默认推荐**，但需结合 `first_page_text` 验证。映射规则：

| source_topic | 默认 vault 分类 | 何时改判 |
|---|---|---|
| `TTS-LLM` | **逐篇判断**——读首页看本质：纯 TTS 系统 → `1-TTS与语音合成`；强调 Speech LLM / audio-LM 架构 → `5-Speech-LLM与AudioLM`；全双工/对话 → `6-全双工与对话` | 必须读 first_page_text 决定 |
| `TTS-core` | `1-TTS与语音合成` | 一般不变 |
| `ControllableTTS` | `1-TTS与语音合成` | 若主要谈韵律/情感/风格 → `11-韵律与情感` |
| `SSL` | `9-语音SSL与表示` | **重要例外**：SSL/ 里可能混入翻译类（如 NLLB / Seamless）→ 改 `10-语音翻译与跨语言`；混入 Speech LLM 类 → `5-Speech-LLM与AudioLM` |
| `speech-codec` | `3-Audio-Codec与Tokenizer` | 一般不变 |
| `VC` | `15-其他音频任务` | 一般不变（VC = Voice Conversion） |
| `RLHF` | `13-训练方法与对齐` | 一般不变 |
| `Survey` | 看 survey 主题决定；强 TTS 综述 → `1-`；语音多模态 → `5-` 或 `7-` | 必读首页 |
| `eval` | `12-数据集与评测` | 一般不变 |
| `Dataset` | `12-数据集与评测` | 一般不变 |
| `tools` | `_待整理`（默认） | 如能从首页看出是某具体方法的工具 → 进对应分类 |

**铁律**：不发明新分类，只用预设 15 + `_待整理`（兜底）。

## Step 3: 为每篇生成 Lite 笔记

### 3.0 架构图选择（**用 WebFetch，不要靠 Python 启发式**）

参考 huangkiki/dailypaper-skills 的 paper-reader 设计：图的**语义判断**（哪张是架构图）由 Claude 通过 WebFetch HTML 完成，Python 只做基础 metadata。

对每篇有 `arxiv_id` 的论文：

1. **WebFetch `https://arxiv.org/html/{arxiv_id}`**（首选）；404 时 fallback `https://ar5iv.labs.arxiv.org/html/{arxiv_id}`
2. 让 Claude 从返回的 HTML / Markdown 里**看 figcaption 文本**：
   - 优先 caption 包含「overall / architecture / framework / pipeline / overview / our model / our framework」的图
   - 优先 Figure 1（多数论文的 Figure 1 就是 overview）
   - 跳过 Table N（不是图）、跳过单字幕 `(a)/(b)`（subfigure 标签）
   - 跳过 ablation / qualitative / loss curve / confusion matrix / t-SNE 这类
3. 选 1-3 张（**多张组合**支持），每张拿 `<img src>` 的绝对 URL
4. 笔记里**直接外链嵌入**：`![Figure N: <caption>](https://arxiv.org/html/{arxiv_id}/x{N}.png)`

**两个 URL 路径坑**（来自 huangkiki/image-troubleshooting.md）：
- 相对路径 `x1.png` → 拼成 `https://arxiv.org/html/{arxiv_id}/x1.png`
- ar5iv 的 `x1.png` 编号**不一定对应论文 Figure 编号**——以 figcaption 文本为准，不要按编号猜
- **检查 URL 不要有重复段**（如 `2603.05312v1/2603.05312v1/x1.png`）

**没有 arxiv_id 或两个 URL 都 404**：跳过图段，整个 `## 🖼 架构图` section 省略，**不要**回退到 pdfimages 或 pdftoppm 整页渲染（用户明确拒绝过整页方案）。

**不验证图可达性**：本 skill 默认接受外链可能未来失效——重要论文用户会去 paper-reader 单独精读。

### 3.1 Method name 抽取（决定文件名）

按优先级：
1. 文件名去掉 `.pdf` 后是干净缩写（如 `VITS` / `XTTS` / `hubert`）→ 直接用，注意大小写规范化（hubert → HuBERT）
2. 文件名是裸 arxiv ID（如 `2409.19510v1`）→ 从 first_page_text 读论文标题/方法名
3. 标题里有「:」前的缩写（如「GSRM: Generative Speech Reward Model」→ `GSRM`）→ 用前缀
4. 都没有 → 从标题前 3-5 个词压一个名（如 `Robust Zero-Shot TTS` → `RZS-TTS`）
5. 实在不行 → 用文件名去 .pdf 原样

文件名要遵循 vault 现有规范（不加年份、不加日期）。

### 3.2 Lite 笔记模板

```markdown
---
title: "<论文完整标题>"
method_name: "<MethodName>"
authors: [<前 3-5 个作者>]
year: <从 arxiv ID 推 / 首页找>
venue: <ICLR / Interspeech / arXiv / ...>
arxiv_id: "<2508.19205 或 null>"
pdf_path: "assets/papers/<MethodName>.pdf"
library_source: "高德文献库"
source_topic: "<source_topic from manifest>"
tags: [classic, <主分类对应的简写如 tts/asr/codec/ssl/speech-llm/vc>]
created: <YYYY-MM-DD>
---

# <MethodName>: <短副标题>

## 📌 一句话

<这篇论文做了什么、属于什么类别、最核心的一个数字或贡献。1-2 句话>

## 🛠 核心方法

**输入 → 输出**: <text→token / waveform→latent / multi-speaker text→long-form speech / ...>

**架构组件**（按数据流顺序列出 2-5 个关键模块）:
1. **<组件 A 名称>**: <一句话功能；首次出现的术语用 [[wikilink]]>
2. **<组件 B 名称>**: <一句话功能>
3. **<组件 C 名称>**: <一句话功能>

**关键创新**: <一两句话讲清楚跟已有方法的本质区别——不要把所有 "first to" 都列上，挑最关键的 1-2 点>

> ⚠️ 上面 3 段是硬结构，**不要合并成自由段落**，否则 lose 了「能扫读」的价值。

## 🖼 架构图

<由 Step 3.x 的 WebFetch arxiv HTML 流程决定。命中 1-3 张架构图就列；都没找到整段省略，**不要**回退到 PDF 整页渲染>

![Figure N: <caption 首 80 字>](https://arxiv.org/html/{arxiv_id}/x{N}.png 或 https://ar5iv.labs.arxiv.org/html/{arxiv_id}/assets/...)

<多张图就分别列；每张图前可加 1 行说明，最多 1 行>

## 📊 关键结果 / 评测

<2-4 行，每行 benchmark 名 + 具体数字。**硬要求**：必须有至少 1 个具体指标。

获取方式（按优先级）：
1. first_page_text 里的数字 → 直接用
2. WebFetch arxiv HTML → 找 Results / Experiments section 的核心 table
3. 都没有（anonymous submission 等）→ 写「匿名投稿，具体数字见论文 Table N」

❌ 禁止：「显著优于」「接近人类水平」等无数字的定性描述
✅ 必须：「LibriSpeech WER 2.1%」「MUSHRA 82.3」「SIM-O 0.796」

例如：
- LibriTTS WER 2.1%, SIM-O 0.68
- Seed-TTS-eval zh: CER 0.95%
- MUSHRA: speech 82.3, music 79.1>

## 💡 借鉴意义（一句话）

<对做 TTS / 全双工 / Audio LLM / ASR / Codec 的人有什么用。没用就直说>

## 🔗 链接

- arXiv: https://arxiv.org/abs/<arxiv_id>（如 null 则省略）
- PDF: [[assets/papers/<MethodName>.pdf|本地 PDF]]
- 源目录: `{source_topic}/{filename}`
```

**字数硬约束**：整篇笔记 **1200-3500 字符**之间（嵌图后体积变大，硬约束相应放宽）。低于 800 字符说明信息不足（mark 为 `_待整理/`），超过 3500 字符说明写多了（精简）。

### 3.3 pdf_tools fallback（无 arxiv_id 或 HTML 404 时）

当 Step 3.0 无法获得外链架构图时（无 arxiv_id / 两个 URL 都 404）：

1. 跑 python3 片段调 `_shared/pdf_tools.extract_images`：
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '$HOME/DailyPaper/skills/_shared')
   import pdf_tools
   imgs = pdf_tools.extract_images('{absolute_path}', '/tmp/library_figs/{MethodName}', 'fig', min_size_bytes=30720)
   for p in sorted(imgs, key=lambda x: x.stat().st_size, reverse=True)[:3]:
       print(p)
   "
   ```
2. 取输出的前 1-3 张（按大小降序，大图更可能是架构图）
3. 复制到 vault：`cp <img> {VAULT_PATH}/assets/papers/figs/{MethodName}_fig{N}.png`
4. 笔记里用相对路径嵌入：`![](assets/papers/figs/{MethodName}_fig1.png)`
5. 如果返回空（PDF 无可用图）→ 省略整个 `## 🖼 架构图` section

**注意**：此 fallback 是**无语义选择**的（无法判断哪张是架构图），仅在 WebFetch 路径失败时才用。架构图 PNG（一般 100-400 KB）走 git，不加 .gitignore。

## Step 4: 批量执行循环

```
read manifest → 按 source_topic 排序（同主题连读，分类思路连贯）
for batch in chunks(entries, 10):
  for entry in batch:
    1. 决定 method_name + vault_category（用 Step 2 规则 + first_page_text）
    2. 生成 Lite 笔记内容（按 Step 3.2 模板）
    3. 写入 {NOTES_PATH}/{category}/{MethodName}.md
       - 文件已存在 → 重命名为 {MethodName}-classic.md（与今日报已有笔记区分）
       - 例外：如果已有同名笔记是更深度的版本（>3 KB），跳过这篇，记到「跳过：已存在更深版本」
    4. Bash: cp "{absolute_path}" "{ASSETS_PATH}/{MethodName}.pdf"
       ⚠️ 目标是 .pdf 文件（二进制复制），**不是** .pdf.md。
       如果 PDF >50 MB 或源文件不存在，跳过并记录到失败列表。
  打印批次进度: "Batch X/9 done (N/90)"

每 3 批做一次 git commit（每 30 篇）：
  - cd {VAULT_PATH}
  - git add 论文笔记/ assets/papers/ -- ':(exclude)*.pdf' 
    （PDF 单独 add，让 gitignore 生效）
  - git add assets/papers/.gitkeep（如果之前没建过）
  - git commit -m "library-import: batch X (N/90)"
  - GIT_PUSH_ENABLED=true 则 git push

最后一批后做最终 commit + push。
```

## Step 5: 处理 PDF 归档 & gitignore

- `mkdir -p {ASSETS_PATH}` 在 Step 0 已做
- 第一次跑时，在 `{ASSETS_PATH}/.gitkeep` 写入空文件，让 git 跟踪这个目录但不跟踪 PDF 本身
- 验证 vault 根的 `.gitignore` 含 `assets/papers/*.pdf`（这是 `library-import` 的前置依赖，**用户应该已经加好了**）。如果没加，**先停**，告诉用户加规则，不要把 191MB PDF 推上 GitHub

## Step 6: 完成报告

最后输出：

```
📚 文献库导入完成

总数: 90 PDF → 87 Lite 笔记 + 2 跳过（已有深度版本）+ 1 失败（_待整理/）

分类分布:
- 1-TTS与语音合成: 28 篇
- 5-Speech-LLM与AudioLM: 18 篇
- 9-语音SSL与表示: 12 篇
- 3-Audio-Codec与Tokenizer: 5 篇
- ...

总耗时: XX 分钟
Git commit: 3 次（main 分支已推送）

下一步建议:
- 查看 _待整理/ 是否需手工归类
- 用 [[wikilink]] grep 看跨论文连接情况
```

## 注意事项

- **不刷 MOC**：导入完不主动跑 `generate_paper_mocs.py`。让用户决定要不要更新索引页（90 篇一进 MOC 会膨胀很大）
- **图按需加**：优先 WebFetch 外链（Step 3.0），其次 pdf_tools fallback（Step 3.3），都不行就省略图段
- **不建概念**：不创建 `_概念/` 下任何文件
- **失败不重试**：单篇失败直接放 `_待整理/{filename}.md` 写错误日志，不阻塞
- **历史 manifest 保留**：跑完后 `/tmp/library_import_manifest.json` 不要删，方便 debug
