# Spec #3: pipeline_guard.py — Phase 5.5 强制化

- 日期：2026-05-20
- 状态：设计完成 → 待 plan
- 关联前置：spec #0（仓库 git 化）、spec #1（HF Trending 已删，age_cutoff 已成主防线）
- 关联后续：spec #2 PDF skill、spec #4 Semantic Scholar 富化

---

## 1. 背景

`daily-papers-review` skill 的 Phase 5.5（Adversarial Self-Review）目前是 prose——5 个子检查写在 SKILL.md 里，靠主 LLM 自觉执行。spec #1 的 retrofit 事故（2026-05-19 必须手工删 3 篇超龄论文）就是这个机制没生效：LLM 写完 draft 没真去对照 age_cutoff，直接保存。整个流水线的"防线"只剩 `fetch_and_score.py` 的 age filter 一道；review 阶段一旦 LLM 走神，老论文就直通日报。

把硬事实检查机械化为 `pipeline_guard.py` 是修这个洞的最直接动作。LLM 仍负责语义判断（过度肯定、自相矛盾），但**无论 LLM 多忙多累，guard 都会硬挡老论文 / 假 wikilink / 缺 evidence triple 这三类"明确错"的 draft**。

---

## 2. 目标

- Phase 5.5.1 / 5.5.3 / 5.5.5 三项硬事实检查由代码强制执行；guard 失败阻断 Phase 6 保存
- LLM 享有 1 轮自修订机会读 guard 的 violations 并定向修复；2 轮还过不了就 BLOCKED 报警 + 落 draft 快照
- Phase 5.5.5 的"自查结果 details 块"不再由 LLM 手写，由 guard JSON 报告自动渲染（消除"假 ✅"风险）
- 5.5.2（过度肯定 / 凭空硬伤）与 5.5.4（自相矛盾）继续是 LLM 在 prose 里自查——guard 不做语义判断
- guard 是无状态 CLI 工具：吃 draft.md + enriched.json + meta.json + notes_dir，吐 JSON + exit code

---

## 3. 范围

### 3.1 范围内

| 文件 | 改动 |
|---|---|
| `skills/_shared/pipeline_guard.py`（新建） | 主体 ~250 行 Python，stdlib 限定 |
| `skills/daily-papers-review/SKILL.md` | Phase 5.5 prose 改为"调 pipeline_guard.py + 走自修订流程"；新增 Phase 5.6 自修订；Phase 5.5.5 改为"嵌入 guard 报告" |
| `scripts/test_pipeline_guard.py`（新建） | 7 个 stdlib 单测（含 fixtures） |
| `scripts/fixtures/guard_*.md`（新建 6 个） | 测试 draft 样本（passing / 各类 violation） |

### 3.2 范围外（不动）

- 其他 skill（paper-reader / library-import / compare / highlights / generate-mocs / notes / weekly）
- `fetch_and_score.py` / `enrich_papers.py`（spec #1 已交付）
- 历史日报 markdown
- LLM 在 5.5.2 / 5.5.4 的语义判断职责——guard **不接管**这两项

---

## 4. 设计

### 4.1 三项强制检查

| ID | 检查 | 数据来源 | 何时算违规 |
|---|---|---|---|
| **C1: date_cutoff** | 推荐论文 `published_date >= meta.age_cutoff` | draft 解析 arxiv id → enriched.json `date` 字段 → meta.json `age_cutoff` | 任一推荐论文 date < cutoff |
| **C2: existing_note_wikilink** | 每条 `📒 **已有笔记**: [[xxx]]` 行的 xxx 在 `{NOTES_PATH}` 下有对应 .md | regex 解析 + glob | 找不到对应文件 |
| **C3: critique_evidence_triples** | 每个非"已有笔记简化格式"的论文段必须有 `🧪 锐评依据:` 块 + ≥2 个 `Claim/Evidence/Confidence` 行 | regex 解析论文段 | 缺块或 triple <2 |

#### 不在范围内的检查（仍由 LLM 在 prose 里自查）
- 5.5.2 过度肯定（"SOTA"/"突破"无证据）
- 5.5.2 凭空硬伤（指控"缺 ablation"但 enriched.section_headers 含 Ablation）
- 5.5.4 借鉴意义 vs 锐评矛盾、分流表等级 vs 锐评 emoji 冲突
- 总评叙事跟实际论文构成不符

理由：这些都需要语义/叙事级判断，机械检测有较高假阳率，强行 hard fail 会绑死 LLM 的措辞自由度。

### 4.2 数据流

```
              ┌────────────────────────┐
              │ Phase 5: LLM 写 draft  │
              └───────────┬────────────┘
                          ↓ Write /tmp/daily_papers_draft.md
              ┌────────────────────────┐
              │ Phase 5.5: pipeline_guard.py│
              │   inputs:                │
              │   - draft.md (positional)│
              │   - --enriched <path>    │
              │   - --meta <path>        │
              │   - --notes <dir>        │
              │   - --json-out <path>    │
              └───────────┬────────────┘
                  exit 0  exit 1
                ┌─────┴───┐ ┌─┴───────────────────────┐
                │         │ │ Phase 5.6: 自修订 (1 轮) │
                │         │ │ - LLM Read JSON          │
                │         │ │ - 按 violation type 修   │
                │         │ │ - 写回 /tmp/draft.md     │
                │         │ │ - 重跑 guard             │
                │         │ └─┬────────────────────────┘
                │         │   exit 0  exit 1
                │         │  ┌──┴──┐  ┌─┴─────────────────────┐
                │         │  │     │  │ cp draft → /tmp/      │
                │         │  │     │  │   draft_blocked_TS.md │
                │         │  │     │  │ + 报 BLOCKED          │
                │         │  │     │  │ + 不 Write vault      │
                ↓         ↓  ↓     ↓  └───────────────────────┘
              ┌────────────────────────┐
              │ Phase 6: Write vault   │
              │  + 嵌 guard report 成  │
              │   self-review details  │
              └────────────────────────┘
```

### 4.3 CLI 契约

```bash
python3 ~/DailyPaper/skills/_shared/pipeline_guard.py \
    /tmp/daily_papers_draft.md \
    --enriched /tmp/daily_papers_enriched.json \
    --meta /tmp/daily_papers_search_meta.json \
    --notes /Users/xiangshu/DailyPaper/DailyPaper/论文笔记 \
    --json-out /tmp/guard_report.json
```

**Exit codes:**
- `0` = all 3 checks passed
- `1` = at least 1 violation; JSON file written; stderr human summary
- `2` = guard internal error（输入文件缺失、JSON 解析失败等）

**Stdout：** 静默（除非 `--verbose` flag）
**Stderr：** 单行 summary `guard: passed` 或 `guard: 3 violations (date_cutoff=1, wikilink_missing=0, triples_missing=2) — see <json-out path>`

### 4.4 JSON 输出 schema

```json
{
  "passed": false,
  "draft_path": "/tmp/daily_papers_draft.md",
  "enriched_path": "/tmp/daily_papers_enriched.json",
  "meta_path": "/tmp/daily_papers_search_meta.json",
  "notes_path": "/Users/xiangshu/DailyPaper/DailyPaper/论文笔记",
  "checked_at": "2026-05-20T14:23:01",
  "summary": {
    "total_violations": 2,
    "by_check": {
      "date_cutoff": 1,
      "existing_note_wikilink": 0,
      "critique_evidence_triples": 1
    },
    "stats": {
      "papers_in_draft": 14,
      "papers_with_existing_note_marker": 3,
      "papers_skipped_for_C3": 3,
      "wikilinks_checked": 3,
      "papers_skipped_no_arxiv_id": 0,
      "papers_no_enrichment_data": 0
    }
  },
  "violations": [
    {
      "check": "date_cutoff",
      "severity": "error",
      "paper_arxiv_id": "2508.19205",
      "paper_title": "VibeVoice: ...",
      "paper_published_date": "2025-08-15",
      "age_cutoff": "2026-05-13",
      "draft_section_header": "### 3. VibeVoice: ...",
      "draft_line": 142,
      "fix_hint": "Remove paper #3 (VibeVoice) — published 2025-08-15 is older than age_cutoff 2026-05-13. Move it to '被排除的论文' section if relevant."
    },
    {
      "check": "critique_evidence_triples",
      "severity": "error",
      "paper_section_header": "### 7. SomePaper",
      "draft_line_start": 198,
      "draft_line_end": 215,
      "triple_count": 1,
      "minimum_required": 2,
      "fix_hint": "Add at least 1 more `Claim/Evidence/Confidence` entry under the 🧪 锐评依据 block of paper #7."
    }
  ]
}
```

### 4.5 解析逻辑（关键正则）

| 解析对象 | 正则 / 方法 |
|---|---|
| 论文段开头 | `re.compile(r'^### (\d+)\. (.+)$', re.MULTILINE)` 切段 |
| arxiv id | 从论文段内匹配 `arxiv\.org/abs/(\d{4}\.\d{4,5})` |
| 论文段是否"已有笔记简化格式" | 检测段内是否含 `📒 \*\*已有笔记\*\*:` 行 |
| 已有笔记 wikilink | `re.compile(r'📒\s*\*\*已有笔记\*\*\s*:\s*\[\[([^\]]+)\]\]')` |
| 锐评依据块 | 从论文段内找 `🧪\s*\*\*锐评依据\*\*` 行起到下一个 `^- \*\*` 或段尾 |
| Claim/Evidence/Confidence triple | block 内 `\` Claim:.*?\` \| \` Evidence:.*?\` \| \` Confidence:` 模式（用 backtick 包裹是约定） |
| Notes glob | `Path(notes_path).rglob(f"{wikilink}.md")` |
| Date 比较 | `datetime.strptime(date_str[:10], "%Y-%m-%d").date()` 对 cutoff |

### 4.6 review SKILL.md 改动

**Phase 5.5 重写为：**
```markdown
### Phase 5.5: 强制自查（pipeline_guard.py）

**写完 Phase 5 → 把 draft 落到 /tmp/daily_papers_draft.md → 调 guard：**

```bash
python3 ../_shared/pipeline_guard.py \
    /tmp/daily_papers_draft.md \
    --enriched /tmp/daily_papers_enriched.json \
    --meta /tmp/daily_papers_search_meta.json \
    --notes "{NOTES_PATH}" \
    --json-out /tmp/guard_report.json
```

- exit 0 → 跳过 Phase 5.6，直接 Phase 6 保存
- exit 1 → 进 Phase 5.6 自修订
- exit 2 → 报 BLOCKED（guard 输入数据有问题，不该硬走）

guard 检的是三件**硬事实**：
1. 日期完整性（C1）：每篇推荐论文 published_date ≥ age_cutoff
2. 已有笔记 wikilink（C2）：📒 **已有笔记**: [[xxx]] 必须对应 vault 真实文件
3. 锐评依据三元组（C3）：每个非已有笔记格式的论文段必须有 🧪 锐评依据 块 + ≥2 triples

**5.5.2（过度肯定/凭空硬伤）和 5.5.4（自相矛盾）guard 不查**——继续靠你（review LLM）prose 级别自查，按原 5.5.2 / 5.5.4 节走一遍。
```

**新增 Phase 5.6：**
```markdown
### Phase 5.6: 自修订（仅在 5.5 失败时）

1. Read /tmp/guard_report.json
2. 按 violations 数组逐条修：
   - **date_cutoff** → 从 draft 中删整个论文段 + 删分流表对应行 + 在「被排除的论文」节加一行说明（标 "spec #3 guard: published {date} 早于 cutoff {cutoff}"）
   - **existing_note_wikilink** → 删那条 `📒 **已有笔记**: [[xxx]]` 行（不删整段）
   - **critique_evidence_triples** → 给指定论文段补 Claim/Evidence/Confidence triple 到 ≥ 2 条
3. 写回 /tmp/daily_papers_draft.md
4. 重跑 pipeline_guard.py（同 Phase 5.5 命令）
5. exit 0 → 进 Phase 6
6. exit 1（第 2 轮还失败）→ 
   ```bash
   cp /tmp/daily_papers_draft.md "/tmp/draft_blocked_$(date +%Y%m%d_%H%M%S).md"
   ```
   告诉用户：「BLOCKED：guard 第 2 轮仍 N 处违规（{summary}），draft 已落到 /tmp/draft_blocked_*.md。请人工修复后改名为 daily_papers_draft.md，再手动跑 Phase 6 或重跑本流水线」
   **不要 Write 到 vault**
```

**Phase 5.5.5 改为（在 Phase 6 保存阶段）：**
```markdown
guard 通过后，把 /tmp/guard_report.json 渲染成自查 details 块嵌到日报末尾：

<details>
<summary>🔍 本次 Adversarial Self-Review 自查结果（pipeline_guard.py 自动）</summary>

| 检查 | 结果 |
|---|---|
| 5.5.1 日期完整性 (C1) | ✅ 全部 N 篇均在 age_cutoff 内 |
| 5.5.5 已有笔记 wikilink (C2) | ✅ 所有 X 个 wikilink 验证通过 |
| 5.5.3 🧪 锐评依据三元组 (C3) | ✅ Y / Y 篇满足 ≥2 triples |
| 5.5.2 事实-证据校对 | ⚙️ LLM 自查（guard 不强制） |
| 5.5.4 自相矛盾扫描 | ⚙️ LLM 自查（guard 不强制） |

guard report: 第 1 轮通过 / 第 2 轮通过（含 K 处自修订）
</details>
```

数字从 guard JSON 的 `summary.stats` 字段直接读，**不要凭记忆填**。

### 4.7 文件组织 / 命名

- guard 主体：`skills/_shared/pipeline_guard.py`（与 user_config.py 同目录，stdlib only，不引 sibling skill）
- 测试：`scripts/test_pipeline_guard.py`，沿用 spec #1 单测的 PASS/FAIL print + sys.exit pattern
- Fixtures：`scripts/fixtures/guard_passing.md`、`guard_date_violation.md`、`guard_wikilink_missing.md`、`guard_triple_missing.md`、`guard_skip_existing_note.md`、`guard_combined.md`（每个 1-3 篇论文，最小可复现）

---

## 5. 错误处理

| 场景 | 行为 |
|---|---|
| draft.md 不存在 | guard exit 2 + stderr "draft not found" |
| enriched.json / meta.json 不存在 | guard exit 2 + stderr 指明哪个缺 |
| draft 里某论文段无 arxiv id（怪 LLM 忘了链接） | C1 跳过该论文（report stats 标 `papers_skipped_no_arxiv_id: N`），不算违规 |
| enriched.json 里查不到该 arxiv id（数据流断） | C1 跳过 + warn `papers_no_enrichment_data: N`，不算违规（因为可能 LLM 引用了一篇没在抓取池的论文，那是另一类 bug 不归 guard） |
| `📒 **已有笔记**: [[名带空格 / 中文]]` | wikilink 解析允许任意非 `]` 字符；glob 用 rglob 直接匹配 |
| 自修订后 LLM 删了一篇论文，分流表 / 「被排除」段忘改 | guard 第 2 轮再跑——分流表行残留不会触发任何 C1/C2/C3，guard 不查表→正文一致性。这是已知盲区，由 LLM prose 自查负责（5.5.4） |
| draft 文件 size > 1 MB | 不该发生；guard 限定 5 MB max read，超过 exit 2 |

---

## 6. 测试计划

`scripts/test_pipeline_guard.py` —— 7 测试，stdlib only：

1. **test_passing_draft**：fixtures/guard_passing.md（3 篇论文，全合格）→ exit 0，summary.total_violations==0
2. **test_date_cutoff_violation**：guard_date_violation.md（含 1 篇 2025-08 论文，cutoff 2026-05-13）→ exit 1，violations 含 date_cutoff entry，arxiv_id 正确
3. **test_existing_note_wikilink_missing**：guard_wikilink_missing.md（含 `📒 **已有笔记**: [[NotExisting]]`）→ exit 1，violations 含 existing_note_wikilink entry
4. **test_critique_triple_missing**：guard_triple_missing.md（某段只有 1 个 triple）→ exit 1，violations 含 critique_evidence_triples entry，paper_section_header 正确
5. **test_skip_existing_note_paper_for_c3**：guard_skip_existing_note.md（一篇标了 `📒 **已有笔记**: [[ValidNote]]`，没 🧪 块）→ C3 应该跳过该段（因为是简化格式），exit 0
6. **test_combined_violations**：guard_combined.md（3 类违规一起）→ exit 1，violations 数组有 3 entries，summary.by_check 各 1
7. **test_enriched_data_missing**：故意传 `--enriched /tmp/nonexistent.json` → exit 2

每个 fixture 文件 < 50 行，用真实日报格式片段（基于 2026-05-20 报告抽取）。

### 端到端验收（不是单测，是手测一次）

- 把 2026-05-19 retrofit 前的 draft（含 OmniFlatten 2024-10、VibeVoice 2025-08、MiniCPM-o-4.5 2026-04）保存为 fixture，用 guard 跑：必须 exit 1 且 3 篇都报为 date_cutoff violation

---

## 7. 验收标准

- [ ] `skills/_shared/pipeline_guard.py` 存在 + import 无 ModuleError
- [ ] `python3 scripts/test_pipeline_guard.py` 7/7 PASS
- [ ] `daily-papers-review/SKILL.md` Phase 5.5 / 5.6 prose 已更新；无残留旧 prose（grep 旧文案如 "翻每一篇被收进推荐的论文" 全无命中）
- [ ] 端到端验收：把模拟 retrofit 前 draft 喂给 guard，exit 1 + 3 个 date_cutoff violations
- [ ] git commit 名 `spec #3: pipeline_guard.py + Phase 5.5 enforced`
- [ ] spec #1 unit test（test_fetch_no_trending.py）仍 7/7 PASS（guard 改 review SKILL.md 不影响 spec #1 的检查）

---

## 8. 风险

- **R1（中）**：LLM 自修订时把段落删错位（删了 ### 3 但分流表里留了对应 wikilink） → guard 第 2 轮不会抓（不查分流表 vs 正文一致性）。**接受**这个盲区——由 5.5.4 LLM prose 自查覆盖；如果未来事故重发可在 spec #5 加 C4 检查
- **R2（低）**：fixture 与未来 SKILL.md 模板格式漂移导致测试假阳性。**缓解**：fixture 注释里写「来自 2026-05-20 真实日报抽样」，未来格式变化时同步改 fixture
- **R3（低）**：`📒 **已有笔记**: [[xxx]]` 的 xxx 含中文空格 → glob 行为正确（Path.rglob 支持 Unicode），单测 fixture 含 1 个中文文件名验证
- **R4（低）**：guard 第 2 轮里 LLM 把 draft 完全重写偏离 Phase 5 原意 → 由 review SKILL.md prose 约束「只重写被点名的段落，别全发」+ `git diff` 不在 spec 范围

---

## 9. 后续 spec 的复用机会

- spec #2 PDF skill 不需要 guard（PDF 处理跟日报无关）
- spec #4 Semantic Scholar 富化可能扩展 C1：除了 arxiv 来源，也支持 DOI 来源的发表日期校验。届时 guard 加一个 `--source-resolver` 选项即可，不破当前契约
- 未来如有 spec #5「全双工 LLM 评测 skill」之类，guard 的解析框架（`### N.` 切段、emoji judgment 提取）可重用
