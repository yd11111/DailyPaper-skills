# Spec #1: 砍掉 HF Trending（daily 路径）

- 日期：2026-05-20
- 状态：已审计 → 设计完成 → 待 plan
- 关联审计：先前会话深度审计（事故 A "老论文泄漏"）
- 前置 ADR：日常 vs 领域调研双路径模型——本 spec 只交付"日常"路径瘦身；"领域调研"另起 spec
- 关联未来 spec：`daily-papers-domain-research-design.md`（未编写）

---

## 1. 背景与动机

### 1.1 事故复盘
2026-05-19 日报需要手工 retrofit，删除 3 篇超龄老论文（OmniFlatten 2024-10、MiniCPM-o-4.5 2026-04、VibeVoice 2025-08）。日报 frontmatter 标了 `age-filter-retrofit` tag。这不是第一次。

### 1.2 根因
`fetch_and_score.py` 的 `merge_and_dedup` 阶段对 HF Trending 来源开了一道日期豁免：
- `TRENDING_AGE_EXEMPTION_UPVOTES = 200`（user-config.json 配置）
- 来源 `hf-trending` 且 `upvotes >= 200` 的论文即使 `published < age_cutoff` 也保留
- 配套：`is_trending=True` 时 `score_paper` 还会再加 score boost
- 配套：周末模式下 `hf-trending + upvotes >= 5` 即使在历史里也允许再推

这条豁免的原意是"如果 HF 上某篇老但超火的论文今天仍是头条素材，别错过"——是个用单一管线硬扛两类需求的妥协。

### 1.3 用户重定义的心智模型
用户明确划分了两条独立的论文搜集路径：
1. **每日搜集论文**——抓今天/最近 N 天的真正新论文（当前 daily 流水线）
2. **领域调研搜集老论文**——主题深挖、追长尾 SOTA（未来独立 skill）

HF Trending 属于路径 2。强行塞进路径 1 是错配。

---

## 2. 目标

- daily 流水线只产出"今日/最近 N 天新发表"的论文
- 移除 HF Trending fetch、scoring boost、age 豁免、weekend re-recommend 四条规则
- 移除后，凡进入日报的论文必须 `published >= age_cutoff`（unconditional）
- HF Trending 代码通过 §8 备份机制保留，未来"领域调研" spec 可复用，但当前不再驻留在 daily 路径

---

## 3. 范围

### 3.1 范围内（必须改）

预先验证：`grep -rli "trending" ~/.claude/skills/` 返回 4 个命中文件，与下表一致。`_shared/user_config.py` 的 DEFAULT_CONFIG 本身就不含 trending 字段，故不在表内。

| 文件 | 改动 | 命中行数 |
|---|---|---|
| `~/.claude/skills/_shared/user-config.json` | 删 `daily_papers.trending_age_exemption_upvotes` 字段（1 行） | 1 |
| `~/.claude/skills/daily-papers/fetch_and_score.py` | 删常量 `TRENDING_AGE_EXEMPTION_UPVOTES`（保留 `MAX_AGE_DAYS`）；`fetch_hf_papers` 删 hf-trending 段（line ~211-230）；`score_paper` 删 `is_trending` 参数 + trending boost 分支（line ~89-104）；`merge_and_dedup` 删 `age_exempted` 字段处理（line ~397-407）+ 删 hf-trending 周末再推分支（line ~463-470）；`stats` meta 同步清理 trending 相关字段；`source_breakdown_of_final` 集合去掉 `hf-trending` | 24 |
| `~/.claude/skills/daily-papers-fetch/SKILL.md` | 删"周末策略"里 HF trending 段（line ~130）；删"hf-trending"来源说明 | 3 |
| `~/.claude/skills/daily-papers-review/SKILL.md` | 删 hf-trending 显示规则（line ~92-95）；删 Phase 5.5.1 里 `age_exempted` 检查（line ~236-237）；删"搜索透明度"模板里 trending exemption 文案（line ~313-321） | 5 |

### 3.2 范围外（明确不动）

- 历史日报 markdown 文件——已手工 retrofit 过，不再追溯
- `.history.json`——任何 trending 标记字段自然失效，不主动清
- `review/notes/weekly/compare/highlights/library-import/generate-mocs/paper-reader/paper-compare/paper-highlights` 的其他逻辑
- `MAX_AGE_DAYS` 配置——age filter 本身保留
- `download_note_images.py`、`enrich_papers.py`、`extract_affiliations.py`

---

## 4. 设计

### 4.1 探讨过的 approach

| 方案 | 描述 | 评价 |
|---|---|---|
| **A. 删干净（采纳）** | 删常量、删函数段、删 SKILL.md 文案。删除前走 §8 备份机制 | 反映用户心智模型；避免死代码；YAGNI |
| B. 配置 flag 关掉 | 留代码、加 `enable_hf_trending: false` 开关，将来 flip 复活 | 污染当前文件；违反"领域调研另起 skill"的决定 |
| C. 拆函数 `fetch_for_daily()` / `fetch_for_trending()` | 预留接口给未来 domain-research skill | 过度设计；接口要等 domain-research spec 才知道形状 |

采纳 A。

### 4.2 删除后的 fetch 数据流

```
解析 --days N
        ↓
fetch_hf_daily(start_date..end_date)   ← 只剩这一路 HF
        +
fetch_arxiv(start_date..end_date, days=N)
        ↓
merge_and_dedup
    ├── age filter（unconditional，无豁免）
    ├── arxiv-id 合并（保留 max score）
    ├── 单天模式：history dedup + score filter + history backfill
    └── 多天模式：跳过 history dedup
        ↓
top_n 切片
        ↓
stdout JSON + /tmp/daily_papers_search_meta.json
```

`score_paper(paper)` 单参数，无 `is_trending`。

### 4.3 stats / meta 简化

`/tmp/daily_papers_search_meta.json` 写入字段裁剪：

```json
{
  "target_date": "YYYY-MM-DD",
  "days_window": N,
  "age_cutoff": "YYYY-MM-DD",
  "age_window_days": N,
  "source_counts": {"hf": <int>, "arxiv": <int>},
  "filter_steps": {
    "age_filter": {"kept": <int>, "dropped_aged": <int>},
    "merged_unique": <int>,
    "history_dedup": <int | "skipped (multi-day mode)">,
    "min_score_filter": {"min_score": 2, "kept": <int>},
    "history_backfilled": <int>
  },
  "config": {
    "arxiv_categories": [...],
    "keywords_count": <int>,
    "negative_keywords_count": <int>,
    "domain_boost_count": <int>,
    "top_n": <int>,
    "min_score": <int>,
    "max_age_days": 7
  },
  "source_breakdown_of_final": {"hf-daily": <int>, "arxiv": <int>},
  "final_count": <int>
}
```

删去：`exempted_hf_trending`、`age_exempted_in_final`、`trending_age_exemption_upvotes`。

`source_breakdown_of_final` 的 source 集合从 `{hf-daily, hf-trending, arxiv}` 缩到 `{hf-daily, arxiv}`。

### 4.4 review SKILL.md 同步

来源格式表（line 92-95）只剩：

- `hf-daily` → `📰 HF Daily，⬆️ {hf_upvotes}`
- `arxiv` → `📄 arXiv 关键词检索`

Phase 5.5.1 第二段（line 236-237）删掉"命中 age_exempted=true 的论文必须显式说明"一段。

文末透明度段（line 313-321）删去"HF 超龄豁免阈值"和"豁免 {exempted}"字样，数据流文案改为：

```
HF {hf} 篇 + arXiv {arxiv} 篇 → 年龄过滤剩 {age_kept}（丢 {age_dropped}）→ 去重 {merged_unique} → 历史去重 {history_kept}（去掉 {history_removed} 已推）→ min_score 过 {score_kept} → 历史回补 {backfill} → **最终 {final_count}**
```

---

## 5. 错误处理 / 退化路径

| 场景 | 行为 |
|---|---|
| HF Daily API 挂 | fetch 返回空列表 + stderr WARN；merge 阶段仅 arxiv 进入下游；日报照常生成（数量取决于 arxiv） |
| arxiv API 挂 | 同理，仅 HF Daily 进入下游 |
| 两者都挂 | merge 入参为空，`top` 为空数组，写 `/tmp/daily_papers_top30.json` = `[]`；review 在前置检查里告知用户"无候选" |
| 候选不足 `min_score` 阈值 | 现有的 history backfill 路径不变；不在本 spec 范围内 |
| 周末 HF Daily 几乎空 | 用户已确认"照跑，能抓几篇算几篇"——不引入特殊周末逻辑 |

---

## 6. 测试

### 6.1 单元（pytest 风格手写脚本即可，不强制接 CI）

写 `/Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py`，覆盖：

1. `score_paper(paper)` 签名只接受 paper 一参；旧调用 `score_paper(paper, is_trending=True)` 抛 TypeError
2. 构造 fake HF Daily + fake arxiv 响应（local fixtures），跑 `fetch_and_score.py --days 1`，断言：
   - 输出 JSON 无 `source == "hf-trending"` 论文
   - 输出 JSON 无 `age_exempted` 字段
   - 每篇 `published >= age_cutoff`（解析 frontmatter meta）
   - `meta.source_breakdown_of_final` 字典 key 只有 `{hf-daily, arxiv}`
   - `meta.config` 无 `trending_age_exemption_upvotes` 键
3. 配置 sanity：`load_user_config()` 返回 dict 无 `daily_papers.trending_age_exemption_upvotes`

### 6.2 集成（人工跑一次）

- 2026-05-20 在真实网络下跑 `python3 ~/.claude/skills/daily-papers/fetch_and_score.py > /tmp/daily_papers_top30.json`
- 检查 stderr 不再有 "Fetching hf-trending..."
- `jq '[.[] | .source] | unique' /tmp/daily_papers_top30.json` 应为 `["arxiv", "hf-daily"]` 或子集
- 跑完整 daily 流水线，目视核对日报无 trending 来源标记

### 6.3 回归

- review skill 的 Phase 5.5 自查折叠块不应再出现 `age_exempted` 字样
- weekly digest 跑一次（覆盖 2026-05-14 ~ 05-20）确认旧报告里 trending 字样不破坏 weekly 解析

---

## 7. 迁移 / 兼容性

- `user-config.json` 删字段后，已部署的脚本读 `daily_papers_config().get("trending_age_exemption_upvotes")` 应返回 None——避免任何残留代码 `KeyError`
- `fetch_and_score.py` 中所有读 `trending_age_exemption_upvotes` 的位置同步删除，不留 `.get()` 兜底
- `.history.json` 中可能存在 `source: "hf-trending"` 或 `age_exempted: true` 的旧条目——只读、不主动迁移；history 30 天过期机制会自然清掉

---

## 8. 备份策略（B1，已定）

**现状**：`~/.claude/skills/` 不是 git 仓库。本 spec 走 B1，仓库重构问题转交未来的 **spec #0**（待写，详见 §11）。

**B1 做法**：
1. `mkdir -p ~/.claude/skills/_backup`
2. 删除任何 trending 相关代码**之前**，先写 `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md`，包含：
   - 5 处删除位置的文件路径 + 起止行号
   - 删除前的原始代码块（含至少 3 行上下文）
   - 每段的删除原因（指向本 spec §1.2）
   - 未来"领域调研"复用提示（HF Trending API endpoint、scoring boost 思路、weekend re-recommend 逻辑）
3. 该 markdown 落盘且自检过后才进入 §3.1 的删除操作

vault inner repo（`/Users/xiangshu/DailyPaper/DailyPaper`）不在本 spec 范围内，不动。

## 11. 关联未来 spec

- **spec #0**（待写）：仓库重构。把所有 paper-相关 skill 从 `~/.claude/skills/` 迁到 `/Users/xiangshu/DailyPaper/skills/` 并通过 symlink 暴露回 `~/.claude/skills/`；`/Users/xiangshu/DailyPaper/` 拉起 git 仓库，把 `scripts/`、`docs/`、`skills/` 都纳管，形成"论文系统独立闭环 repo"。spec #0 完成后，未来所有 paper-skill 改动（含 spec #2/#3/#4）走 git。本 spec #1 的 B1 备份在 spec #0 落地后会被 git history 取代，可移除。

---

## 9. 验收标准

- [ ] `fetch_and_score.py` grep `trending` 全文无命中（除非在注释里解释"已迁出 daily"）
- [ ] `user-config.json` grep `trending` 无命中
- [ ] `daily-papers-fetch/SKILL.md` 与 `daily-papers-review/SKILL.md` grep `trending` 无命中
- [ ] 单元测试 6.1 全过
- [ ] 集成 6.2 跑通且日报里没有 `🔥 HF Trending` 标记
- [ ] review skill 输出的"搜索透明度"段无 "HF 超龄豁免阈值" 文案

---

## 10. 风险与放弃方案

- **风险 R1**：删完发现 HF Daily 几个月没更新（API 改了），arxiv 也不够，日报每日只有 2-3 篇——但这是数据源问题，跟本 spec 决策无关；用户已接受"周末照跑"逻辑可推广到平日
- **风险 R2**：未来"领域调研" skill 想要 HF Trending fetcher 时，从 `~/.claude/skills/_backup/hf-trending-removed-2026-05-20.md` 拷代码（spec #0 落地后改用 git history）
- **放弃方案**：如果 spec #1 上线 1 周后用户反馈日报太瘦，从 §8 备份原路恢复 5 处删除；后续讨论是否做"领域调研" spec
