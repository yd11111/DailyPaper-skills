#!/usr/bin/env python3
"""扫一个本地 PDF 文献库，输出 manifest JSON（默认 temp_file_path）。

**只做基础 metadata**——图选择由 SKILL.md 里 Claude 用 WebFetch 处理（参考
huangkiki/dailypaper-skills 的 paper-reader 设计：让 LLM 做语义判断，Python
只处理机械事）。

用法:
    python3 build_manifest.py <library_root> [--out manifest.json]

每篇 PDF 抽取：
  - filename, absolute_path, relative_path, source_topic (用户已分类目录)
  - first_page_text (pdftotext -l 1 拿到的首页文本，含标题 + 摘要)
  - arxiv_id (regex 从首页找到的话填，否则 null)
  - file_size_bytes
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent.parent / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from arxiv_id import extract_id as _extract_arxiv_id  # noqa: E402
import pdf_tools as _pdf_tools  # noqa: E402
from user_config import temp_file_path as _temp_file_path  # noqa: E402


def extract_first_page(pdf_path: Path) -> str:
    """用 pdf_tools.extract_text 抽首页。失败返回空串。"""
    return _pdf_tools.extract_text(pdf_path, first_n_pages=1, timeout=30)


def find_arxiv_id(text: str) -> str | None:
    """在文本中找 arxiv ID。返回首个匹配（最可能在 URL 或脚注里）。"""
    return _extract_arxiv_id(text) or None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("library_root", help="文献库根目录")
    parser.add_argument("--out", default=str(_temp_file_path("library_import_manifest.json")))
    args = parser.parse_args()

    root = Path(args.library_root).expanduser().resolve()
    if not root.is_dir():
        print(f"[ERR] {root} 不是目录", file=sys.stderr)
        return 2

    pdfs = sorted(root.rglob("*.pdf"))
    print(f"[manifest] 找到 {len(pdfs)} 个 PDF", file=sys.stderr)

    entries = []
    for i, pdf in enumerate(pdfs, 1):
        rel = pdf.relative_to(root)
        topic = rel.parts[0] if len(rel.parts) > 1 else "_root"
        text = extract_first_page(pdf)
        text_clip = text[:3000] if text else ""
        entry = {
            "filename": pdf.name,
            "absolute_path": str(pdf),
            "relative_path": str(rel),
            "source_topic": topic,
            "first_page_text": text_clip,
            "first_page_chars": len(text),
            "arxiv_id": find_arxiv_id(text) if text else None,
            "file_size_bytes": pdf.stat().st_size,
        }
        entries.append(entry)
        if i % 20 == 0:
            print(f"[manifest] 进度 {i}/{len(pdfs)}", file=sys.stderr)

    topic_counts = Counter(e["source_topic"] for e in entries)
    print(f"[manifest] 主题分布: {dict(topic_counts)}", file=sys.stderr)
    with_arxiv = sum(1 for e in entries if e["arxiv_id"])
    print(f"[manifest] 找到 arxiv ID: {with_arxiv}/{len(entries)}", file=sys.stderr)
    print(f"[manifest] PDF 抽取失败（无文本）: {sum(1 for e in entries if not e['first_page_text'])}", file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"[manifest] 写入 {out_path} ({len(entries)} entries)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
