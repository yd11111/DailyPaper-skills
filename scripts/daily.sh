#!/bin/zsh
# 每日 9:00 由 launchd 触发，跑一次「今日论文推荐」并桌面通知
set -uo pipefail

LOG_DIR=/Users/xiangshu/DailyPaper/scripts
LOG="$LOG_DIR/daily.log"
NOTIFY="$LOG_DIR/notify.sh"
WORK_DIR=/Users/xiangshu/DailyPaper
VAULT=/Users/xiangshu/DailyPaper/DailyPaper
DAILY_PAPERS_DIR="$VAULT/DailyPapers"

mkdir -p "$LOG_DIR"
exec >> "$LOG" 2>&1
echo ""
echo "===== $(date '+%Y-%m-%d %H:%M:%S') run start ====="

# launchd 启动的 shell 不会继承终端的 PATH/HOME，显式补上
export HOME=/Users/xiangshu
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

# Python.org Python 3.12 默认 cafile 为空，arxiv 等 HTTPS 会 SSL verify failed
# 用 certifi 自带 CA bundle 修复
if command -v python3 >/dev/null 2>&1; then
  CERTIFI_PEM=$(python3 -c "import certifi; print(certifi.where())" 2>/dev/null)
  [[ -n "$CERTIFI_PEM" && -f "$CERTIFI_PEM" ]] && export SSL_CERT_FILE="$CERTIFI_PEM"
fi

# 国内网络 huggingface.co 走不通，用 hf-mirror.com 镜像
export HF_ENDPOINT=https://hf-mirror.com

cd "$WORK_DIR"

# 跑论文流水线（--print 让 Claude 跑完非交互输出后退出）
claude --dangerously-skip-permissions --print "今日论文推荐" \
  > "$LOG_DIR/claude.stdout.log" 2> "$LOG_DIR/claude.stderr.log"
rc=$?
echo "claude exit code: $rc"

# 找今天的推荐文件（默认 .md 文件名包含日期）
TODAY=$(date '+%Y-%m-%d')
REPORT=$(ls -t "$DAILY_PAPERS_DIR"/${TODAY}*.md 2>/dev/null | head -1)
if [[ -z "$REPORT" ]]; then
  # 兜底：拿最新的
  REPORT=$(ls -t "$DAILY_PAPERS_DIR"/*.md 2>/dev/null | head -1)
fi

if [[ $rc -eq 0 && -n "$REPORT" && -f "$REPORT" ]]; then
  COUNT=$(grep -c '^### [0-9]\+\.' "$REPORT" 2>/dev/null || echo 0)
  REPORT_NAME=$(basename "$REPORT")
  "$NOTIFY" "今日论文推荐已生成" "${COUNT} 篇 · ${REPORT_NAME}"
  echo "OK: $REPORT (#$COUNT papers)"
else
  "$NOTIFY" "论文推荐失败" "查看 $LOG"
  echo "FAIL: rc=$rc, report='$REPORT'"
fi

echo "===== run end (exit $rc) ====="
exit $rc
