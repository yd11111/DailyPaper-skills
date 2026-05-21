# Spec #2: `_shared/pdf_tools.py` — PDF 工具集中封装

- 日期：2026-05-20
- 状态：设计完成 → 待 plan
- 关联前置：spec #0（git 仓库就位）、spec #1（HF Trending 已删）、spec #3（pipeline_guard 已上线，TDD + subprocess test pattern 可复用）
- 关联未来：spec #4（Semantic Scholar）可能引入 DOI lookup，不依赖本 spec；library-import 修复（`.pdf.md` 空文件 + Step 3.3 自相矛盾）是另起 spec

---

## 1. 背景

审计（先前会话）发现 PDF 处理散在 3 个文件里，每处自己写 subprocess + 自己处理失败：

| 文件 | 现有片段 |
|---|---|
| `skills/library-import/build_manifest.py:33` | `subprocess.run(["pdftotext", "-l", "1", str(pdf_path), "-"], capture_output=True, timeout=30)` |
| `skills/daily-papers/enrich_papers.py:346` | `cmd = f'curl -sL ... "{url}" \| pdftotext -l 2 - - \| {EXTRACT_AFFILIATIONS_SCRIPT}'` 三段 shell pipe |
| `skills/daily-papers/download_note_images.py:151` | `subprocess.create_subprocess_exec("pdfimages", "-png", pdf_path, prefix)` + 自己 glob + size filter |

3 处都各自 try/except → 返空（silently fail）。后果：
- 同一 bug（如未来要换 binary path 或加 retry）得在 3 处修
- spec #4 / spec #5 加新 PDF 用法时不知道在哪扩展
- library-import 的 figure 处理矛盾（Step 3.3 写 `/tmp/library_figs` 但根本没有脚本生成）一部分根源就是 PDF 工具不在 `_shared/`，没人想着先封装

---

## 2. 目标

- 1 个 stdlib 模块 `skills/_shared/pdf_tools.py`，2 个公开函数：`extract_text`、`extract_images`
- 3 个 caller 同时迁移过去，**保留各自现有的"PDF 失败 silently 返空"语义**
- 错误模型分两层：binary 缺位 raise（部署问题）、PDF 解析 / 网络 fail 返空（数据问题）
- 单测覆盖 local path 分支；URL 分支只在 caller migration smoke 里验
- 不引入 pdfplumber / pdftoppm（caller 没用，YAGNI）

---

## 3. 范围

### 3.1 范围内

| 文件 | 改动 |
|---|---|
| `skills/_shared/pdf_tools.py`（新建） | 主体 ~80 行 stdlib |
| `scripts/test_pdf_tools.py`（新建） | ~120 行 stdlib，6 个单测（URL 分支 1 测改 manual smoke） |
| `scripts/fixtures/sample.pdf`（新建） | 1 页文本 + 1 张较大嵌入图（≥ 10 KB），用于 extract_text + extract_images 联合验证 |
| `skills/library-import/build_manifest.py` | `extract_first_page()` 内部改为调 `pdf_tools.extract_text(path, first_n_pages=1)` |
| `skills/daily-papers/enrich_papers.py` | `extract_affiliations_pdf()` 拆 shell pipe → `(1)` 调 `pdf_tools.extract_text(url, first_n_pages=2)` `(2)` 用 stdin 把 text 喂给 `extract_affiliations.py` 子进程 |
| `skills/daily-papers/download_note_images.py` | `try_pdf_extract()` 里的 pdfimages 段 → 调 `pdf_tools.extract_images(pdf_path, assets_dir, prefix, min_size_bytes=10240)` |
| 3 个 git commits（模块+测试 / build_manifest / enrich_papers + download_note_images） | — |

### 3.2 范围外

- `extract_affiliations.py` 本身（仍是 stdin → JSON stdout 脚本，spec #2 不动其内部 regex）
- `pdfplumber`（无 caller）
- `pdftoppm` 整页渲染（无 caller）
- library-import 的 `.pdf.md` 空文件 bug、Step 3.3 自相矛盾、figure 处理整体重构（**专门 spec**）
- `paper-reader/references/image-troubleshooting.md` 等 prose（仅文档；模块上线后可在 cleanup spec 里改链接）
- 其他 skill / pipeline_guard / 历史日报 / 内层 vault

### 3.3 已验证的前置事实

- 实际 PDF 工具 call site = 3（grep 确认）
- pdftotext / pdfimages 已在用户机上可用（3 个 caller 现在都跑得动）
- `extract_affiliations.py` 用 stdin → JSON stdout 接口，**不需要**改这个文件就能配合迁移
- ~/DailyPaper 是 git 仓库（spec #0 落地后），per-task commits 可走

---

## 4. 设计

### 4.1 公开 API

```python
def extract_text(
    input: str | Path,
    first_n_pages: int | None = None,
    timeout: int = 30,
) -> str:
    """Extract plain text from a PDF.

    input:
      - URL string (starts with 'http://' or 'https://')
        → `curl -sL --max-time T <url> | pdftotext [-l N] - -`
      - Path or str path (local file)
        → `pdftotext [-l N] <path> -`

    first_n_pages: if set, only extract pages 1..N (uses `pdftotext -l N`)
    timeout: per-subprocess timeout in seconds (default 30)

    Returns:
      extracted text on success;
      "" on PDF parse failure, network failure, or local file missing.

    Raises:
      RuntimeError — if `pdftotext` binary not found, or if URL input
                     and `curl` binary not found.
    """


def extract_images(
    pdf_path: str | Path,
    out_dir: str | Path,
    prefix: str,
    min_size_bytes: int = 10240,
) -> list[Path]:
    """Extract images from a local PDF using pdfimages.

    Writes `<out_dir>/<prefix>-NNN.png` and returns the list of Paths
    sorted by name, filtered to those with size >= min_size_bytes
    (default 10 KB; intended to drop tiny icons / decorations).

    Returns:
      list of Path objects (possibly empty if no images >= min_size).

    Raises:
      RuntimeError — if `pdfimages` binary not found.
      FileNotFoundError — if `pdf_path` does not exist.
    """
```

### 4.2 内部组织

```python
"""pdf_tools.py — spec #2: centralized PDF text + image extraction.

Stdlib only. Wraps `pdftotext` (text) and `pdfimages` (images)
from poppler-utils. URL inputs are pipe-fetched via `curl`.

Callers: build_manifest.py, enrich_papers.py, download_note_images.py.
"""

import shutil
import subprocess
from pathlib import Path


def _check_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(
            f"{name} not installed; install poppler via `brew install poppler` "
            f"(or your platform's equivalent)"
        )


def _is_url(s: object) -> bool:
    return isinstance(s, str) and s.startswith(("http://", "https://"))


def _pdftotext_args(first_n_pages: int | None) -> list[str]:
    return ["-l", str(first_n_pages)] if first_n_pages else []


def _extract_text_local(path: Path, first_n_pages, timeout) -> str: ...
def _extract_text_url(url: str, first_n_pages, timeout) -> str: ...

def extract_text(input, first_n_pages=None, timeout=30) -> str: ...
def extract_images(pdf_path, out_dir, prefix, min_size_bytes=10240) -> list[Path]: ...
```

Implementation detail：
- `_extract_text_local`：`subprocess.run(["pdftotext"] + _pdftotext_args(...) + [str(path), "-"], capture_output=True, text=True, timeout=timeout)`，try/except 返 ""
- `_extract_text_url`：`subprocess.run("curl -sL --max-time T <url> | pdftotext [-l N] - -", shell=True, capture_output=True, text=True, timeout=timeout+5)`，try/except 返 ""
- `extract_images`：`subprocess.run(["pdfimages", "-png", str(pdf), str(out_dir/prefix)], check=True, capture_output=True, timeout=timeout)`，try/except → 返 [];成功后 `sorted(out_dir.glob(f"{prefix}-*.png"))` + size filter

### 4.3 Caller 迁移映射

#### 4.3.1 `build_manifest.py`

旧：
```python
def extract_first_page(pdf_path: Path) -> str:
    try:
        r = subprocess.run(
            ["pdftotext", "-l", "1", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
```

新：
```python
import sys
from pathlib import Path
_SHARED_DIR = Path(__file__).resolve().parent.parent / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from pdf_tools import extract_text

def extract_first_page(pdf_path: Path) -> str:
    return extract_text(pdf_path, first_n_pages=1, timeout=30)
```

（已经有现成的 sibling-import 套路，参考 `enrich_papers.py` 的 `_SHARED_DIR` 模式。）

#### 4.3.2 `enrich_papers.py.extract_affiliations_pdf`

旧（3 段 shell pipe）：
```python
cmd = (
    f'curl -sL --max-time {CURL_TIMEOUT} "https://arxiv.org/pdf/{arxiv_id}"'
    f" | pdftotext -l 2 - -"
    f" | {sys.executable} {EXTRACT_AFFILIATIONS_SCRIPT}"
)
proc = await asyncio.create_subprocess_shell(cmd, ...)
stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=CURL_TIMEOUT + 15)
if stdout:
    data = json.loads(stdout.decode(...))
    affils = data.get("affiliations", [])
```

新（两阶段，保留 async）：
```python
# Stage 1: get PDF text (sync, wrapped in to_thread)
text = await asyncio.to_thread(
    pdf_tools.extract_text,
    f"https://arxiv.org/pdf/{arxiv_id}",
    first_n_pages=2,
    timeout=CURL_TIMEOUT,
)
if not text:
    continue  # retry

# Stage 2: feed text to extract_affiliations.py via stdin
proc = await asyncio.create_subprocess_exec(
    sys.executable, EXTRACT_AFFILIATIONS_SCRIPT,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.DEVNULL,
)
stdout, _ = await asyncio.wait_for(
    proc.communicate(input=text.encode("utf-8")),
    timeout=CURL_TIMEOUT + 5,
)
if stdout:
    data = json.loads(stdout.decode("utf-8", errors="replace"))
    affils = data.get("affiliations", [])
    if affils:
        return affils
```

行为等价：原 shell pipe `curl|pdftotext|extract_affiliations` 三段顺序流；新代码也是三段，只是 stage 1 用 to_thread 包同步函数，stage 2 显式 asyncio subprocess。性能差异忽略不计（PDF 下载 + pdftotext 是 IO bound）。

#### 4.3.3 `download_note_images.py.try_pdf_extract`

旧：
```python
# Extract images with pdfimages
proc = await asyncio.create_subprocess_exec(
    "pdfimages", "-png", pdf_path, prefix,
    stdout=asyncio.subprocess.DEVNULL,
    stderr=asyncio.subprocess.DEVNULL,
)
await asyncio.wait_for(proc.communicate(), timeout=30)
# Find extracted images > 10KB
extracted = sorted(assets_dir.glob(f"{method_name}_pdf_fig-*.png"))
large = [f for f in extracted if f.stat().st_size > 10240]
```

新：
```python
large = await asyncio.to_thread(
    pdf_tools.extract_images,
    pdf_path,
    assets_dir,
    f"{method_name}_pdf_fig",
    min_size_bytes=10240,
)
```

注意：`min_size_bytes=10240` 等价旧的 `> 10240`（>= 10241 vs > 10240 差 1 字节，无实际影响；正式实现 `>=` 跟 spec 一致；下方 §6 测试用 ≥ 10240 验）。

### 4.4 文件组织

- `skills/_shared/pdf_tools.py` — 跟 user_config.py 同目录，pattern 一致
- `scripts/test_pdf_tools.py` — 跟 spec #1 / #3 单测同一目录
- `scripts/fixtures/sample.pdf` — 跟 spec #3 fixtures 同一目录；用 `pdftoppm` 或 Mac `cupsfilter` 从一个 markdown 印 PDF 出来（生成步骤记录在 spec 附录），尺寸 ~50 KB，含 1 页文字 + 1 张嵌入图 PNG ≥ 10 KB

---

## 5. 错误处理

| 场景 | 行为 |
|---|---|
| `pdftotext` / `pdfimages` / `curl` 未安装 | raise RuntimeError(包含 `brew install poppler` 提示) |
| local PDF 文件不存在（extract_text 时） | 返 `""`（跟 build_manifest 旧行为一致；pdftotext 自己会失败） |
| local PDF 文件不存在（extract_images 时） | raise FileNotFoundError（programmer 错——download_note_images caller 总是先 download_image 才调） |
| PDF 损坏 / pdftotext 退出非零 | 返 `""` |
| pdftotext 超时 | 返 `""` |
| URL 网络超时 / 429 / 5xx | 返 `""`（curl 自己处理超时，subprocess 接 stdout='' 即可） |
| pdfimages segfault 或 CalledProcessError | 返 `[]` |
| out_dir 不存在 | extract_images 内部 `mkdir(parents=True, exist_ok=True)` |
| out_dir 不可写 | OSError 透传给 caller（部署/权限问题） |

---

## 6. 测试计划

`scripts/test_pdf_tools.py` 6 个单测（stdlib only，沿用 spec #3 的 PASS/FAIL print + sys.exit pattern）：

1. **test_extract_text_local** — 喂 `scripts/fixtures/sample.pdf`，断言返回字符串含 "Sample PDF" 子串（fixture 印 PDF 时埋的标记字符串）
2. **test_extract_text_first_n_pages** — 同 fixture，first_n_pages=1，验证只拿首页；fixture 可以是 2 页 PDF，第 2 页有独占字符串 "Page Two Only"，断言**不**含
3. **test_extract_text_missing_file** — 喂 `/tmp/nonexistent.pdf` → 返 `""`
4. **test_extract_images** — 同 fixture，验证返 `list[Path]` 长度 ≥ 1 且每个 `.stat().st_size >= 10240`
5. **test_extract_images_pdf_missing** — raise FileNotFoundError
6. **test_binary_missing_raises** — monkey-patch `pdf_tools._check_binary` 或 `shutil.which` 让 pdftotext "缺位" → raise RuntimeError

**不测**：URL 路径（test_extract_text_url）——用户已确认，URL 分支只在 caller migration smoke 里跑一次（见 §7）。

### fixture 生成步骤（spec 附录，工程师执行）

```bash
# Use python+reportlab or fallback to a 2-page PDF with one >=10KB image
# Recommended: a tiny LaTeX source compiled with pdflatex, OR
# a Python script using reportlab that writes a 2-page PDF with a sample image.
# Concrete recipe in plan Task 2.
```

Plan 会给出确切的 fixture 生成命令（用 `reportlab` 或 Mac `cupsfilter`），sample.pdf 落到 `scripts/fixtures/sample.pdf` 并提交。

---

## 7. 验收

- [ ] `skills/_shared/pdf_tools.py` 存在、import 无错、`extract_text` 和 `extract_images` 函数签名与 §4.1 一致
- [ ] `scripts/test_pdf_tools.py` 6/6 PASS
- [ ] `build_manifest.py.extract_first_page` 迁移后 spot-check：跑一个已知 PDF（如 vault 里 `assets/papers/HuBERT.pdf`，如果还在），返回的字符串与旧实现等价（含 "HuBERT" 字样）
- [ ] `enrich_papers.py.extract_affiliations_pdf` 迁移后 smoke：跑一个真 arxiv id（用 fixtures/enriched.json 里的 2605.10000 也行——本地 fake URL，跳过此条；或随便挑一个 arxiv id 联网验），返回 affiliations 非空（如果该论文本来 affil 可解析）
- [ ] `download_note_images.py.try_pdf_extract` 迁移后 smoke：跑一个有图的 arxiv 论文（如 HuBERT 之前用过的），本地化后 figs 数量 ≥ 1
- [ ] spec #1 单测（test_fetch_no_trending.py）7/7 PASS（pdf_tools 加入不影响 fetch 路径）
- [ ] spec #3 单测（test_pipeline_guard.py）7/7 PASS（pdf_tools 加入不影响 guard 路径）
- [ ] 3 个 git commits 落地、working tree clean、`git log --oneline` 含本 spec 全部 commits

---

## 8. 风险

- **R1（中）**：enrich_papers 迁移把 3 段 shell pipe 拆成 Python 两阶段。理论等价但 async 行为可能略不同；smoke 必须跑一次真论文确认 affiliations 没变质。如果 affiliations 大幅退化 → 回滚 enrich_papers migration（保留模块 + 其他 2 caller），单独 spec 再处理
- **R2（低）**：sample.pdf 跨 macOS pdftotext 版本输出可能略不同（空格 / 换行）。测试断言用 `in` 子串匹配，不用 exact
- **R3（低）**：fixture PDF 嵌入图大小因生成方式不同 — 测试 `min_size_bytes=10240` 卡死，但 fixture 可能产出 8 KB 图导致测试失败。Plan 中给出明确的生成步骤 + 图 ≥ 15 KB 的保险参数
- **R4（低）**：未来 spec #4 / #5 加新 PDF 用法（render_page、pdfplumber）时 1-2 行加进 pdf_tools.py，不需要重设计；本 spec 不预留

---

## 9. 后续 spec 复用

- spec #4 Semantic Scholar 富化：如果 SS 返的论文有 DOI 但无 arxiv id，可能想用 pdf_tools.extract_text(doi_pdf_url, first_n_pages=2) 抽 affiliations。复用 0 改动
- 未来 library-import 重构：图选择走 pdf_tools.extract_images 作 last fallback。复用 0 改动
- 未来"PDF 全文搜索"或"PDF 表格抽取"功能：在 pdf_tools 加 `extract_tables` + pdfplumber 依赖，不破当前 API
