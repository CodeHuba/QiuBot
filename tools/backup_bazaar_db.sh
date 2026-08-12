#!/bin/bash
# 每日备份 bazaar_runs.db
# 保留最近 7 天备份

DB="/opt/qiubot/data/bazaar_runs.db"
BACKUP_DIR="/data0809/qiubot/backups"
DATE=$(date +%Y%m%d)
BACKUP="$BACKUP_DIR/bazaar_runs.$DATE.db"
LOG="/opt/qiubot/logs/backup.log"

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname $LOG)"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始备份..." >> "$LOG"

# 用 sqlite3 online backup（安全，不影响运行中的写操作）
if python3 -c "
import sqlite3, sys
src = sqlite3.connect('$DB')
dst = sqlite3.connect('$BACKUP')
src.backup(dst)
src.close()
dst.close()
print('ok')
" >> "$LOG" 2>&1; then
    SIZE=$(du -sh "$BACKUP" | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份成功: $BACKUP ($SIZE)" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份失败!" >> "$LOG"
    exit 1
fi

# 清理 7 天前的备份
find "$BACKUP_DIR" -name 'bazaar_runs.*.db' -mtime +7 -delete
REMAINING=$(ls "$BACKUP_DIR"/bazaar_runs.*.db 2>/dev/null | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 当前保留备份数: $REMAINING" >> "$LOG"
