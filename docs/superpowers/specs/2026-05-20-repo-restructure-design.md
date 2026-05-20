# Spec #0: 仓库重构（最小版）

- 日期：2026-05-20
- 状态：设计完成 → 待 plan
- 关联前置：spec #1 已落地（HF Trending 已删，`_backup/` 已建）
- 关联后续：spec #2/#3/#4 全部走本 spec 建立的 git 仓库提交

---

## 1. 背景

`~/.claude/skills/` 不是 git 仓库。spec #1 因此走 B1 备份策略（手写 markdown 归档），是临时方案。本 spec 把整套 paper 系统作为闭环放进一个独立 git 仓库 `~/DailyPaper/`，让后续所有 spec 都能走 git history。

当前 `~/DailyPaper/` 已经持有 `scripts/`（cron + 测试）、`docs/`（specs/plans）、内层 vault `DailyPaper/`，以及 `.claude/settings.json`（HF 镜像 + SSL 证书路径）。本 spec 把 12 个 paper skills 从 `~/.claude/skills/` 搬进 `~/DailyPaper/skills/`，通过 symlink 让 Claude Code 继续在原位识别它们。

---

## 2. 目标

- `~/DailyPaper/` 成为独立 git 仓库
- 12 个 paper skills 实际驻留 `~/DailyPaper/skills/<name>/`
- `~/.claude/skills/<name>` 全部变为指向 `~/DailyPaper/skills/<name>` 的目录 symlink
- Claude Code 加载 skills 0 感知差异；spec #1 单元测试仍 7/7 PASS
- LaunchAgents / settings.json / 内层 vault / scripts 路径 0 影响
- 后续 spec 写代码改 skills 的提交直接走 `cd ~/DailyPaper && git commit`

---

## 3. 范围

### 3.1 范围内（必须做）

| 动作 | 内容 |
|---|---|
| 移动 12 个 dir | `~/.claude/skills/{_backup, _shared, daily-papers, daily-papers-fetch, daily-papers-notes, daily-papers-review, daily-papers-weekly, generate-mocs, library-import, paper-compare, paper-highlights, paper-reader}` → `~/DailyPaper/skills/` |
| 12 个 symlink | `~/.claude/skills/<name>` → `/Users/xiangshu/DailyPaper/skills/<name>`（绝对路径目录软链） |
| `git init` | 在 `~/DailyPaper/` |
| `.gitignore` | 排除：内层 `DailyPaper/`、`*.log`、`__pycache__/`、`*.pyc`、`.DS_Store`、`.claude/settings.local.json`（防御性） |
| 初始 commit | `import paper system from ~/.claude/skills/ (spec #0)` |

### 3.2 范围外（明确不动）

- `_backup/` 内容随 skills 走，不重组到 docs/
- `scripts/*.log` 文件不删，仅 gitignore
- 不写 README、不重组 scripts/、不动 LaunchAgents、不动 `.claude/settings.json` 内容
- 内层 vault `~/DailyPaper/DailyPaper/` 完全不动；它自带 git 仓库
- skills 内文件**内容**不动（搬运而已）

### 3.3 已验证的前置事实

- `scripts/` 内 0 处 hardcoded `~/.claude/skills/` 路径（`grep -rn .claude/skills /Users/xiangshu/DailyPaper/scripts/` 无输出）
- `_shared/` 模块用 `Path(__file__).resolve().parent.parent` 解析路径，对 symlink 透明
- 仅 2 个 SKILL.md 文件（`daily-papers-review/SKILL.md`、`library-import/SKILL.md`）在 prose 里写到 `~/.claude/skills/` 字面路径——这些是文档说明，symlink 后字面路径仍可达
- 内层 vault `~/DailyPaper/DailyPaper/.git` 存在，是独立仓库
- 外层 `~/DailyPaper/` 当前没有 `.git` 也没有 `.gitignore`

---

## 4. 设计

### 4.1 探讨过的 approach

| 方案 | 描述 | 评价 |
|---|---|---|
| **A. cp + verify + rm + symlink**（采纳） | 12 个 skill 各自：`cp -a` 到新位置 → `diff -rq` 校验 → `rm -rf` 原位 → `ln -s` 建 symlink。完整 cp+verify 阶段先于任何 rm | 12 步原子化；中途死，cp 半成品在新位置，原位完整可恢复 |
| B. mv + symlink | `mv ~/.claude/skills/<n> ~/DailyPaper/skills/<n> && ln -s ...` | 简洁但 mv 不可逆；中途死会留半截状态 |
| C. cp → symlink → 延后 rm | 不删原位，让两份共存 | 浪费磁盘 + 未来 spec 改 skill 不知道改哪份 → 拒绝 |

### 4.2 操作流（伪代码，plan 会细化到 bash 命令）

```
0. mkdir -p ~/DailyPaper/skills/
1. for skill in 12个:
     cp -a ~/.claude/skills/$skill ~/DailyPaper/skills/$skill
     diff -rq ~/.claude/skills/$skill ~/DailyPaper/skills/$skill  # 0 差异
2. 全部 cp 完后 + 全部 diff 通过后:
     for skill in 12个:
       rm -rf ~/.claude/skills/$skill
       ln -s /Users/xiangshu/DailyPaper/skills/$skill ~/.claude/skills/$skill
3. 跑 spec #1 单元测试，7/7 PASS 才进 git
4. cd ~/DailyPaper
   写 .gitignore
   git init
   git add .gitignore skills/ scripts/ docs/ .claude/settings.json
   git status  # 人工 review，确认无 DailyPaper/ 内层条目
   git commit -m "import paper system from ~/.claude/skills/ (spec #0)"
```

### 4.3 `.gitignore` 完整内容

```gitignore
# 内层 Obsidian vault 自带 git 仓库，外层不跟踪
DailyPaper/

# 运行时日志
*.log
scripts/*.log

# Python 编译产物
__pycache__/
*.pyc
*.pyo

# macOS
.DS_Store

# Claude Code 本地覆盖配置（环境特异）
.claude/settings.local.json
.claude/*.local.json

# 临时 / 缓存
/tmp/
*.tmp
*.swp
```

### 4.4 symlink 类型与解析

- 用绝对路径目录 symlink：`ln -s /Users/xiangshu/DailyPaper/skills/<n> /Users/xiangshu/.claude/skills/<n>`
- macOS `ls -la ~/.claude/skills/` 会显示 `<name> -> /Users/xiangshu/DailyPaper/skills/<name>`
- Python `Path(__file__).resolve()` 会跟随 symlink 解析到真实路径；`_shared` 模块的相对 import 不受影响
- Claude Code 读 skill 目录的行为：把 `~/.claude/skills/<name>/SKILL.md` 当 SKILL 文件解析；symlink 透明可读

---

## 5. 错误处理 / 回滚

| 场景 | 行为 |
|---|---|
| cp 阶段死（磁盘满 / 权限错） | 原位完整，删 `~/DailyPaper/skills/` 半成品 → 状态回到 0 |
| diff 阶段发现差异（不应发生） | 报错列差异；不进 rm/symlink，原位仍可用 |
| rm + symlink 中途死（极小概率，因为这是 12 个独立 ln -s 命令） | 已 rm + 已 symlink 的 skill 走新位置可用；未处理的 skill 还在原位可用。但**混合状态会让 spec #1 的单元测试找不到部分 skill**——必须**所有 rm+ln 完成**才能算 step 2 done |
| Claude Code 重启后认不到 skill | 检查 `readlink ~/.claude/skills/<name>` 是否指向有效路径；如失败，从备份（cp 阶段的原文件还在 `~/DailyPaper/skills/<name>/`）重建 symlink |
| `git init` 把 inner vault 拉进去 | `.gitignore` 第一条就 `DailyPaper/`；`git status` 必须人工 review，看不到 `DailyPaper/` 条目才 commit |
| LaunchAgents 在 cron 时间触发，撞上重构过程 | 重构在 1 分钟内完成；如担心，前置 `launchctl unload ~/Library/LaunchAgents/com.xiangshu.dailypaper.plist` + weekly 同样 unload，完成后重 load。本 spec 默认信任时间窗口，不强制 unload |

---

## 6. 验收标准

- [ ] `ls -la ~/.claude/skills/` 显示 12 个 symlink，无任何普通目录
- [ ] `readlink ~/.claude/skills/daily-papers` == `/Users/xiangshu/DailyPaper/skills/daily-papers`（spot-check 一个就行）
- [ ] `du -sh ~/.claude/skills/ ~/DailyPaper/skills/` 显示前者 < 5 KB（纯 symlink），后者承载所有内容
- [ ] `ls ~/DailyPaper/skills/` 显示 12 个真实目录
- [ ] `python3 /Users/xiangshu/DailyPaper/scripts/test_fetch_no_trending.py` → 7/7 PASS（证明 import 链路通）
- [ ] `python3 ~/.claude/skills/daily-papers/fetch_and_score.py 2>&1 | head -5` 不抛 ImportError（端到端 smoke，HF 跑通即可，arxiv 429 不阻塞）
- [ ] `cd ~/DailyPaper && git status` 显示 working tree clean
- [ ] `cd ~/DailyPaper && git log --stat -1 | grep -c "^ DailyPaper/"` 返回 0（内层 vault 没被拉进 commit；行首空格防止误匹配 `~/DailyPaper/skills/`）
- [ ] `cd ~/DailyPaper && git log --stat -1` 的输出**同时**包含 `skills/`、`scripts/`、`docs/`、`.gitignore`、`.claude/settings.json` 这 5 个路径条目（逐一 grep 验证，每项必须命中至少 1 次）

---

## 7. 风险评估

- **R1（中）**：Claude Code 当前会话已经识别到的 skill paths 是绝对路径还是相对路径？如果是绝对路径，重构后下次 Claude Code 启动时才生效。本 spec 接受这个延迟——重构完成后下次会话生效
- **R2（低）**：spec #1 单元测试已经验证了 `import fetch_and_score`，重构后再跑一次即可。如果 Python sys.path 缓存有问题，新 Python 进程不受影响
- **R3（低）**：LaunchAgents 用 `~/DailyPaper/scripts/daily.sh`，路径不变；脚本里 `python3 ~/.claude/skills/...` 通过 symlink 解析，OK
- **R4（很低）**：将来用户在 `~/.claude/skills/` 装非 paper-相关的新 skill 时，新装的会落在 `~/.claude/skills/` 真目录中（与 paper symlinks 混存）——这是无害的；spec #0 不限制未来扩展

---

## 8. 后续 spec 受益

- **spec #2**（PDF skill）：`cd ~/DailyPaper && git add skills/pdf/ && git commit` 直接走
- **spec #3**（pipeline_guard）：同上
- **spec #4**（Semantic Scholar/OpenAlex 富化）：同上；`.claude/settings.json` 或 `_shared/user-config.json` 加 API key 字段都走 git
- 任何未来 spec 涉及 skills 内容修改都可直接 `git commit -m "spec #N: ..."`，无需再写手工备份 markdown
- `_backup/hf-trending-removed-2026-05-20.md` 可在 spec #0 落地后任何时刻删除（git history 已取代它）——但本 spec 不主动删
