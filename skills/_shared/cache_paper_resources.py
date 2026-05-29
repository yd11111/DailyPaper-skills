#!/usr/bin/env python3
"""一站式论文资源本地化下载。

下载并缓存：
- arXiv PDF 到 cache/papers/{arxiv_id}/paper.pdf
- arXiv HTML 到 cache/papers/{arxiv_id}/paper.html
- 提取的图表到 vault/{paper_notes}/_resources/{arxiv_id}/figures/
- GitHub repo（如有）到 cache/papers/{arxiv_id}/github/{org}_{repo}/
- meta.json 元数据到 cache/papers/{arxiv_id}/meta.json

设计原则（详见 ~/DailyPaper/skills/paper-reader/references/no-hallucination-rules.md §11.5）：
- 重型资源（PDF / HTML / GitHub clone）→ vault 外 cache（不进 git，不让 Obsidian 索引）
- 图表（轻型）→ vault 内 _resources/（Obsidian wikilink 友好，加 .gitignore 排除）

CLI 用法：
    python3 cache_paper_resources.py 2601.15621 \\
        --github https://github.com/QwenLM/Qwen3-TTS \\
        --no-clone-github  # 可选：跳过 clone

返回 JSON 到 stdout：含所有本地路径，供 paper-reader 写入 frontmatter。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from user_config import (
    cache_papers_dir,
    default_clone_github,
    paper_notes_dir,
    timeouts_config,
    vault_resources_dir,
)


HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (paper-reader cache) DailyPaper/1.0",
}


def log(msg: str) -> None:
    print(f"[cache] {msg}", file=sys.stderr)


def http_download(url: str, dest: Path, timeout: int = 60) -> bool:
    """下载文件到本地，返回 True 表示成功。已存在且非空则跳过。"""
    if dest.exists() and dest.stat().st_size > 0:
        log(f"跳过已存在: {dest.name} ({dest.stat().st_size} bytes)")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tmp = dest.with_suffix(dest.suffix + ".part")
            with tmp.open("wb") as f:
                shutil.copyfileobj(resp, f)
            tmp.rename(dest)
        log(f"下载完成: {dest.name} ({dest.stat().st_size} bytes)")
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        log(f"下载失败 {url}: {e}")
        if dest.with_suffix(dest.suffix + ".part").exists():
            dest.with_suffix(dest.suffix + ".part").unlink()
        return False


def fetch_pdf(arxiv_id: str, dest_dir: Path, timeout: int) -> Path | None:
    """下载 arXiv PDF。"""
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    dest = dest_dir / "paper.pdf"
    if http_download(url, dest, timeout):
        return dest
    # fallback: 不带版本号的格式
    url2 = f"https://arxiv.org/pdf/{arxiv_id}"
    if http_download(url2, dest, timeout):
        return dest
    return None


def fetch_html(arxiv_id: str, dest_dir: Path, timeout: int) -> Path | None:
    """下载 arXiv HTML（用于离线 grep 引文 / 章节结构 verify）。"""
    url = f"https://arxiv.org/html/{arxiv_id}"
    dest = dest_dir / "paper.html"
    if http_download(url, dest, timeout):
        # 检查是否真的是 HTML（404 会返回错误页面）
        head = dest.read_bytes()[:200].lower()
        if b"<html" not in head and b"<!doctype" not in head:
            log(f"HTML 内容看起来不对，删除: {dest}")
            dest.unlink()
            return None
        return dest
    return None


def extract_figures(
    pdf_path: Path, figures_dir: Path, prefix: str = "fig"
) -> list[Path]:
    """从 PDF 提取图表到 vault 内 _resources/{arxiv_id}/figures/。

    使用 _shared/pdf_tools.extract_images（spec #2 集中化封装）。
    """
    if not pdf_path.exists():
        return []
    try:
        from pdf_tools import extract_images
    except ImportError:
        log("pdf_tools 不可用，跳过图表提取")
        return []
    figures_dir.mkdir(parents=True, exist_ok=True)
    try:
        images = extract_images(
            str(pdf_path), str(figures_dir), prefix=prefix, min_size_bytes=10 * 1024
        )
        log(f"提取 {len(images)} 张图到 {figures_dir}")
        return [Path(p) for p in images]
    except Exception as e:
        log(f"图表提取失败: {e}")
        return []


def clone_github(github_url: str, dest_dir: Path, depth: int = 1) -> Path | None:
    """clone GitHub repo 到 cache/papers/{arxiv_id}/github/{org}_{repo}/。

    返回 clone 后的本地路径，失败返回 None。
    """
    # 解析 github_url -> org/repo
    url = github_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    if "github.com/" not in url:
        log(f"非 GitHub URL: {github_url}")
        return None
    parts = url.split("github.com/", 1)[1].split("/")
    if len(parts) < 2:
        log(f"GitHub URL 解析失败: {github_url}")
        return None
    org, repo = parts[0], parts[1]
    target = dest_dir / f"{org}_{repo}"
    if target.exists() and (target / ".git").exists():
        log(f"GitHub repo 已存在: {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "git",
        "clone",
        f"--depth={depth}",
        f"https://github.com/{org}/{repo}.git",
        str(target),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=300, capture_output=True, text=True)
        log(f"GitHub clone 完成: {target}")
        return target
    except subprocess.CalledProcessError as e:
        log(f"GitHub clone 失败 ({org}/{repo}): {e.stderr[:200] if e.stderr else e}")
        return None
    except subprocess.TimeoutExpired:
        log(f"GitHub clone 超时: {org}/{repo}")
        return None


def cache_paper(
    arxiv_id: str,
    github_url: str | None = None,
    clone_github_repo: bool | None = None,
    extract_figures_from_pdf: bool = True,
    timeout: int | None = None,
) -> dict:
    """主入口：缓存一篇论文的全部资源。

    返回 dict 包含：
        - arxiv_id
        - cache_dir: cache/papers/{arxiv_id}/
        - pdf_local: 本地 PDF 路径（None 表失败）
        - html_local: 本地 HTML 路径
        - figures_dir: vault 内 _resources/{arxiv_id}/figures/
        - github_local: GitHub clone 路径（None 表跳过或失败）
        - meta_path: meta.json 路径
    """
    if clone_github_repo is None:
        clone_github_repo = default_clone_github()
    if timeout is None:
        timeout = int(timeouts_config().get("arxiv_fetch", 60))

    # vault 外重型 cache 目录
    cache_dir = cache_papers_dir() / arxiv_id
    cache_dir.mkdir(parents=True, exist_ok=True)

    # vault 内轻型 _resources 目录（图表）
    vault_resources = vault_resources_dir() / arxiv_id
    figures_dir = vault_resources / "figures"

    pdf_path = fetch_pdf(arxiv_id, cache_dir, timeout)
    html_path = fetch_html(arxiv_id, cache_dir, timeout)

    figures: list[Path] = []
    if extract_figures_from_pdf and pdf_path:
        figures = extract_figures(pdf_path, figures_dir, prefix=f"fig")

    github_path: Path | None = None
    if github_url and clone_github_repo:
        github_path = clone_github(github_url, cache_dir / "github")

    meta = {
        "arxiv_id": arxiv_id,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "github_url": github_url,
        "sources": {
            "pdf": str(pdf_path) if pdf_path else None,
            "html": str(html_path) if html_path else None,
            "figures_dir": str(figures_dir) if figures else None,
            "figures_count": len(figures),
            "github_local": str(github_path) if github_path else None,
        },
    }
    meta_path = cache_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # 计算 vault 相对路径（用于 frontmatter 的 figures_dir 字段，便于 Obsidian wikilink）
    figures_relative: str | None = None
    if figures:
        try:
            figures_relative = str(figures_dir.relative_to(paper_notes_dir()))
        except ValueError:
            figures_relative = str(figures_dir)

    return {
        "arxiv_id": arxiv_id,
        "cache_dir": str(cache_dir),
        "pdf_local": str(pdf_path) if pdf_path else None,
        "html_local": str(html_path) if html_path else None,
        "figures_dir_abs": str(figures_dir) if figures else None,
        "figures_dir_relative": figures_relative,
        "figures_count": len(figures),
        "github_local": str(github_path) if github_path else None,
        "meta_path": str(meta_path),
        "cached_at": meta["fetched_at"][:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="缓存论文资源到本地")
    parser.add_argument("arxiv_id", help="arXiv ID，如 2601.15621")
    parser.add_argument("--github", help="GitHub repo URL（可选）", default=None)
    parser.add_argument(
        "--no-clone-github",
        action="store_true",
        help="跳过 GitHub clone（覆盖默认）",
    )
    parser.add_argument(
        "--no-extract-figures",
        action="store_true",
        help="跳过 PDF 图表提取",
    )
    parser.add_argument(
        "--timeout", type=int, default=None, help="HTTP 超时秒数"
    )
    args = parser.parse_args()

    clone_flag: bool | None = None
    if args.no_clone_github:
        clone_flag = False

    result = cache_paper(
        args.arxiv_id,
        github_url=args.github,
        clone_github_repo=clone_flag,
        extract_figures_from_pdf=not args.no_extract_figures,
        timeout=args.timeout,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
