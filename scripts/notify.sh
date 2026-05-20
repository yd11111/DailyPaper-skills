#!/bin/zsh
# Usage: notify.sh "Title" "Message"
TITLE="${1:-DailyPaper}"
MSG="${2:-}"
# osascript 是 macOS 自带的，无需额外安装
osascript -e "display notification \"${MSG//\"/\\\"}\" with title \"${TITLE//\"/\\\"}\" sound name \"Glass\""
