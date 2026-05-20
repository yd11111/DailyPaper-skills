# HF Trending Removal — Backup Archive

**Date:** 2026-05-20
**Spec:** /Users/xiangshu/DailyPaper/docs/superpowers/specs/2026-05-20-cut-hf-trending-design.md
**Reason:** Repeated "old paper leak" incidents (2026-05-19 retrofit dropped OmniFlatten 2024-10, MiniCPM-o-4.5 2026-04, VibeVoice 2025-08). HF Trending's age-exemption was the leak vector. User has decided to split daily vs domain-research into two pipelines; this code belongs to the future "domain research" skill, not daily.

This file preserves the deleted code so a future `daily-papers-domain-research` skill can re-use the fetch + scoring logic. Once spec #0 (repo restructure) is done and `~/.claude/skills/` is under git, this archive can be removed in favor of `git show <commit>`.

---

## 1. user-config.json — trending exemption field

**File:** `~/.claude/skills/_shared/user-config.json`
**Removed line:** `"trending_age_exemption_upvotes": 200` (plus trailing comma on preceding `"max_age_days": 7,` line)

---

## 2. fetch_and_score.py — TRENDING_AGE_EXEMPTION_UPVOTES constant

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (pre-edit, captured Step 2)

```python
# 论文 published date 距离今天最大允许天数；超龄一律剔除（HF Trending 把老 hot paper 顶上来的根治办法）
MAX_AGE_DAYS = _CONFIG.get("max_age_days", 7)
# 例外：HF Trending 的爆款（upvotes >= 此阈值）即使超龄也保留，避免漏真 SOTA。设为 None 关闭例外
TRENDING_AGE_EXEMPTION_UPVOTES = _CONFIG.get("trending_age_exemption_upvotes", 200)
```

---

## 3. fetch_and_score.py — score_paper trending boost branch

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (pre-edit, captured Step 2)

Removed: `is_trending` parameter, `keyword_hits` counter, entire "# 4. Trending boost" branch.

```python
# ── Scoring ────────────────────────────────────────────────────────────────


def score_paper(paper: dict, is_trending: bool = False) -> int:
    text = (paper["title"] + " " + paper["abstract"]).lower()
    title_lower = paper["title"].lower()

    # 1. Negative keywords → instant reject
    for neg in NEGATIVE_KEYWORDS:
        if neg in text:
            return -999

    score = 0

    # 2. Positive keywords
    keyword_hits = 0
    for kw in KEYWORDS:
        if kw in title_lower:
            score += 3
            keyword_hits += 1
        elif kw in text:
            score += 1
            keyword_hits += 1

    # 3. Domain boost
    domain_hits = sum(1 for kw in DOMAIN_BOOST_KEYWORDS if kw in text)
    if domain_hits >= 2:
        score += 2
    elif domain_hits == 1:
        score += 1

    # 4. Trending boost (HF sources only)
    #    GATE: only apply if paper has at least 1 keyword or domain match,
    #    to prevent irrelevant but popular papers from flooding the list
    has_relevance = keyword_hits > 0 or domain_hits > 0
    if is_trending:
        upvotes = paper.get("hf_upvotes", 0) or 0
        if has_relevance:
            # Relevant + trending → full boost
            if upvotes >= 10:
                score += 3
            elif upvotes >= 5:
                score += 2
            elif upvotes >= 2:
                score += 1
        else:
            # No relevance → minimal boost (only very popular papers get a chance)
            if upvotes >= 20:
                score += 1

    return score
```

---

## 4. fetch_and_score.py — _parse_hf_item trending dispatch

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (pre-edit, captured Step 2)

```python
    is_trending = source == "hf-trending"
    paper["score"] = score_paper(paper, is_trending=is_trending)
```

Replaced with: `paper["score"] = score_paper(paper)`

---

## 5. fetch_and_score.py — fetch_hf_papers hf-trending block

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (pre-edit, captured Step 2)

Removed (full block, from comment "# ── hf-trending: always single call (not date-dependent) ──" through the items loop):

```python
    # ── hf-trending: always single call (not date-dependent) ──
    endpoint = f"{_HF_BASE}/api/daily_papers?sort=trending&limit=50"
    print(f"  Fetching hf-trending...", file=sys.stderr)
    raw = fetch_url(endpoint)
    if raw:
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = []
            print(f"  [WARN] bad JSON from hf-trending", file=sys.stderr)
        for item in items:
            result = _parse_hf_item(item, "hf-trending")
            if result:
                arxiv_id, paper = result
                if arxiv_id not in papers or paper["score"] > papers[arxiv_id]["score"]:
                    papers[arxiv_id] = paper
```

### Reuse notes for future domain-research skill:
- Endpoint: `{HF_BASE}/api/daily_papers?sort=trending&limit=50`
- Score boost tiered by upvotes (10/5/2 thresholds, +3/+2/+1 score)
- Relevance gate: only boost if keyword_hits + domain_hits > 0

---

## 6. fetch_and_score.py — age-exemption branch in merge_and_dedup

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (pre-edit, captured Step 2)

Removed: `aged_exempted = 0` initializer, the entire `if TRENDING_AGE_EXEMPTION_UPVOTES is not None and p.get("source") == "hf-trending"...` branch, the conditional log suffix `f" / exempted {aged_exempted} HF爆款"`, and the stats key `"exempted_hf_trending": aged_exempted`.

```python
    hf_papers: list[dict],
    arxiv_papers: list[dict],
    target_date,
    days: int = 1,
    top_n: int = TOP_N,
) -> list[dict]:
    is_weekend = target_date.weekday() >= 5

    # ── age filter: drop papers older than today - (days_window + MAX_AGE_DAYS) ──
    # 单天模式 days=1 → 窗口 = MAX_AGE_DAYS（默认 7 天）
    # 多天模式 days=7 → 窗口 = MAX_AGE_DAYS + 6（容忍跨周抓取）
    # 这是真正治本的过滤，**所有源**一视同仁，杜绝 HF Trending 把 2024 年老 hot paper 顶上来
    age_window = MAX_AGE_DAYS + (days - 1)
    age_cutoff = target_date - timedelta(days=age_window)
    aged_out = 0
    aged_exempted = 0
    age_filtered: list[dict] = []
    # 收集 search meta（供 review 阶段写入日报 frontmatter）
    stats: dict = {
        "target_date": target_date.isoformat(),
        "days_window": days,
        "age_cutoff": age_cutoff.isoformat(),
        "age_window_days": age_window,
        "source_counts": {
            "hf": len(hf_papers),
            "arxiv": len(arxiv_papers),
        },
        "filter_steps": {},
    }
    for p in hf_papers + arxiv_papers:
        pub_str = (p.get("date") or "").strip()
        if not pub_str:
            age_filtered.append(p)  # 无日期信息，放过（极少见）
            continue
        try:
            pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
        except ValueError:
            age_filtered.append(p)
            continue
        if pub_date >= age_cutoff:
            age_filtered.append(p)
            continue
        # 超龄。例外：HF Trending 爆款（upvotes 极高）保留
        upvotes = p.get("hf_upvotes") or 0
        if (
            TRENDING_AGE_EXEMPTION_UPVOTES is not None
            and p.get("source") == "hf-trending"
            and upvotes >= TRENDING_AGE_EXEMPTION_UPVOTES
        ):
            p["age_exempted"] = True  # 让后续 review 阶段可显式标注
            age_filtered.append(p)
            aged_exempted += 1
            continue
        aged_out += 1
    print(
        f"  Age filter (cutoff={age_cutoff}, window={age_window}d): "
        f"kept {len(age_filtered)} / dropped {aged_out}"
        + (f" / exempted {aged_exempted} HF爆款" if aged_exempted else ""),
        file=sys.stderr,
    )
    stats["filter_steps"]["age_filter"] = {
        "kept": len(age_filtered),
        "dropped_aged": aged_out,
        "exempted_hf_trending": aged_exempted,
    }
```

---

## 7. fetch_and_score.py — weekend re-recommend trending branch

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (pre-edit, captured Step 2)

Removed:

```python
    # ── cross-day dedup ──
    deduped: dict[str, dict] = {}
    removed = 0
    for aid, p in by_id.items():
        if aid in history_ids:
            # Weekend: keep trending with upvotes >= 5
            if is_weekend and p.get("source") == "hf-trending" and (p.get("hf_upvotes") or 0) >= 5:
                p["is_re_recommend"] = True
                p["last_recommend_date"] = history_ids[aid]
                deduped[aid] = p
            else:
                removed += 1
        else:
            deduped[aid] = p
```

Also removed `is_weekend = target_date.weekday() >= 5` initializer in merge_and_dedup (became unused).

---

## 8. fetch_and_score.py — meta config & source_breakdown_of_final

**File:** `~/.claude/skills/daily-papers/fetch_and_score.py` (pre-edit, captured Step 2)

Removed: `"trending_age_exemption_upvotes": TRENDING_AGE_EXEMPTION_UPVOTES` from meta.config; `"hf-trending"` from the `source_breakdown_of_final` set comprehension; entire `"age_exempted_in_final": sum(...)` key.

```python
    # 写一份 search meta 到 /tmp，供 review skill 读取以加进日报 frontmatter
    from user_config import temp_file_path
    meta = {
        **stats,
        "config": {
            "arxiv_categories": ARXIV_CATEGORIES,
            "keywords_count": len(KEYWORDS),
            "negative_keywords_count": len(NEGATIVE_KEYWORDS),
            "domain_boost_count": len(DOMAIN_BOOST_KEYWORDS),
            "top_n": TOP_N,
            "min_score": MIN_SCORE,
            "max_age_days": MAX_AGE_DAYS,
            "trending_age_exemption_upvotes": TRENDING_AGE_EXEMPTION_UPVOTES,
        },
        "source_breakdown_of_final": {
            s: sum(1 for p in top if p.get("source") == s)
            for s in {"hf-daily", "hf-trending", "arxiv"}
        },
        "age_exempted_in_final": sum(1 for p in top if p.get("age_exempted")),
    }
```

---

## 9. daily-papers-fetch/SKILL.md — trending mentions

```
70-
71-脚本自动完成：
72:- 并行抓取 HuggingFace Daily + Trending API 和 arXiv API
73:- 关键词打分（正向/负向/领域加分/trending 加分）
74-- 按 arXiv ID 合并去重
75-- 读取 `.history.json` 跨天去重（含周末模式放宽规则）
--
128-- 如果 arXiv API 抓取失败，脚本自动 fallback 到仅 HuggingFace 源
129-- 如果总论文数不足 20 篇，有多少处理多少
130:- **周末策略**：arXiv 周末不更新，HF daily 周末基本为空，但 HF trending 持续更新。周末主要依赖 trending 来源
131-- **不做 git 操作**，不生成推荐文件，只输出临时 JSON
```

---

## 10. daily-papers-review/SKILL.md — trending source format + age_exempted check + transparency template

```
88-#### 数据来源提醒
89-
90:每篇论文的 `source`（hf-daily / hf-trending / arxiv）和 `hf_upvotes` 来自抓取数据，必须保留到输出中。`method_summary` 来自富化数据，用于撰写核心方法描述。
91-
92-**来源格式规则**（按 source 字段分别显示）：
93-- `hf-daily` → `📰 HF Daily，⬆️ {hf_upvotes}`
94:- `hf-trending` → 🔥 HF Trending，⬆️ {hf_upvotes}`
95-- `arxiv` → `📄 arXiv 关键词检索`（不显示 upvotes，因为没有）
96-
--
233-- 读取 `/tmp/daily_papers_search_meta.json`，记下 `age_cutoff`
234-- 翻每一篇被收进推荐的论文，在 enriched 数据里看它的 `date` 字段
235:- 任何一篇 `date < age_cutoff` 且**没有** `age_exempted: true` 标记 → **立刻从推荐表删掉**，理由写到「被排除的论文」节
236:- 命中 `age_exempted: true` 的论文，必须在锐评里**显式说明**「这是被超龄豁免进来的 HF 爆款（upvotes={n}），不是本周新论文」
237-
238-#### 5.5.2 事实-证据校对
--
294-    history_deduped: <n>
295-    final: <n>
296:  source_breakdown_of_final: {hf-daily: <n>, hf-trending: <n>, arxiv: <n>}
297:  age_exempted_in_final: <n>   # > 0 时说明日报里有「超龄豁免的 HF 爆款」
298----
299-```
--
314-- **关键词数**：{keywords_count} 正向 / {negative_keywords_count} 负向 / {domain_boost_count} 加分
315-- **打分门槛**：min_score = {min_score}
316:- **HF 超龄豁免阈值**：upvotes ≥ {trending_age_exemption_upvotes}
317:- **数据流**：HF {hf} 篇 + arXiv {arxiv} 篇 → 年龄过滤剩 {age_kept}（丢 {age_dropped}，豁免 {exempted}） → 去重 {merged_unique} → 历史去重 {history_kept}（去掉 {history_removed} 已推） → min_score 过 {score_kept} → 历史回补 {backfill} → **最终 {final_count}**
318:- **最终入选来源**：HF Daily {n} + HF Trending {n} + arXiv {n}{；含超龄豁免 N 篇 if > 0}
319-
320-> 数字全部来自 fetch_and_score.py 的 `/tmp/daily_papers_search_meta.json`，不是我编的。修改阈值改 `~/.claude/skills/_shared/user-config.json`。
```
