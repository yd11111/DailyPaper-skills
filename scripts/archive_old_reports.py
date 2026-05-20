#!/usr/bin/env python3
"""把 DailyPapers/ 下 >30 天的 YYYY-MM-DD-*.md 用 git mv 归档到 Archive/YYYY-MM/。

被周报脚本 weekly.sh 在跑周报前调用一次。
跳过 Weekly/、Archive/、.history.json 等。
"""

import datetime
import re
import subprocess
import sys
from pathlib import Path

VAULT = Path("/Users/xiangshu/DailyPaper/DailyPaper")
DAILY = VAULT / "DailyPapers"
ARCHIVE_ROOT = DAILY / "Archive"
KEEP_DAYS = 30
NAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-.+\.md$")


def main() -> int:
    if not DAILY.is_dir():
        print(f"[archive] {DAILY} 不存在，跳过", file=sys.stderr)
        return 0

    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=KEEP_DAYS)

    moves: list[tuple[Path, Path]] = []
    for f in sorted(DAILY.iterdir()):
        if not f.is_file():
            continue
        m = NAME_RE.match(f.name)
        if not m:
            continue
        try:
            file_date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if file_date >= cutoff:
            continue
        target_dir = ARCHIVE_ROOT / f"{m.group(1)}-{m.group(2)}"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f.name
        moves.append((f, target))

    if not moves:
        print(f"[archive] 无 >30 天的旧报告（cutoff={cutoff}），跳过", file=sys.stderr)
        return 0

    for src, dst in moves:
        rc = subprocess.run(
            ["git", "mv", str(src.relative_to(VAULT)), str(dst.relative_to(VAULT))],
            cwd=VAULT,
        ).returncode
        if rc != 0:
            print(f"[archive] git mv 失败：{src} → {dst}", file=sys.stderr)
            return rc
        print(f"[archive] moved: {src.name} → Archive/{dst.parent.name}/", file=sys.stderr)

    # commit + push 留给外部 weekly.sh 或 daily-papers-weekly skill 来做
    print(f"[archive] 共归档 {len(moves)} 个文件，未自动 commit", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
