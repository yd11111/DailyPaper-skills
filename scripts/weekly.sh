#!/bin/zsh
# 周五 12:07 由 launchd 触发
# 1) 归档 DailyPapers/ 下 >30 天的报告到 Archive/YYYY-MM/
# 2) 跑 daily-papers-weekly skill 生成本周综述
# 3) commit + push + 桌面通知
set -uo pipefail

LOG_DIR=/Users/xiangshu/DailyPaper/scripts
LOG="$LOG_DIR/weekly.log"
NOTIFY="$LOG_DIR/notify.sh"
WORK_DIR=/Users/xiangshu/DailyPaper
VAULT=/Users/xiangshu/DailyPaper/DailyPaper
WEEKLY_DIR="$VAULT/DailyPapers/Weekly"

mkdir -p "$LOG_DIR"
exec >> "$LOG" 2>&1
echo ""
echo "===== $(date '+%Y-%m-%d %H:%M:%S') weekly start ====="

# launchd 启动的 shell 缺 PATH / HOME / SSL / HF
export HOME=/Users/xiangshu
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
if command -v python3 >/dev/null 2>&1; then
  CERTIFI_PEM=$(python3 -c "import certifi; print(certifi.where())" 2>/dev/null)
  [[ -n "$CERTIFI_PEM" && -f "$CERTIFI_PEM" ]] && export SSL_CERT_FILE="$CERTIFI_PEM"
fi
export HF_ENDPOINT=https://hf-mirror.com

cd "$WORK_DIR"

# Step 1: 归档老报告（仅做 git mv，不 commit；下一步 commit 会捎带）
echo "--- step 1: archive old reports ---"
python3 "$LOG_DIR/archive_old_reports.py"
archive_rc=$?
echo "archive rc: $archive_rc"

# Step 2: 跑 weekly skill
echo "--- step 2: run weekly digest skill ---"
claude --dangerously-skip-permissions --print "本周论文总结" \
  > "$LOG_DIR/weekly.claude.stdout.log" 2> "$LOG_DIR/weekly.claude.stderr.log"
claude_rc=$?
echo "claude rc: $claude_rc"

# Step 3: 兜底 commit & push（skill 自己应该 commit 了，这里是保险）
echo "--- step 3: ensure committed & pushed ---"
cd "$VAULT"
if [[ -n "$(git status --porcelain DailyPapers/)" ]]; then
  git add DailyPapers/
  git commit -m "weekly: $(date '+%Y-W%V')（archive + digest 兜底提交）" || true
fi
git push 2>&1 || echo "push failed (offline?)"

# Step 4: 通知
REPORT=$(ls -t "$WEEKLY_DIR"/*.md 2>/dev/null | head -1)
if [[ $claude_rc -eq 0 && -n "$REPORT" && -f "$REPORT" ]]; then
  REPORT_NAME=$(basename "$REPORT")
  "$NOTIFY" "本周论文综述已生成" "$REPORT_NAME"
  echo "OK: $REPORT"
else
  "$NOTIFY" "周报失败" "查看 weekly.log"
  echo "FAIL: claude_rc=$claude_rc, report='$REPORT'"
fi

echo "===== weekly end (claude rc $claude_rc, archive rc $archive_rc) ====="
exit $claude_rc
