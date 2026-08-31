#!/bin/bash
# 每日备份 bazaar_runs.db
# 上传到腾讯云 COS，本地只保留最近 2 天

DB="/opt/qiubot/data/bazaar_runs.db"
BACKUP_DIR="/data0809/qiubot/backups"
DATE=$(date +%Y%m%d)
BACKUP="$BACKUP_DIR/bazaar_runs.$DATE.db"
LOG="/opt/qiubot/logs/backup.log"
COSCMD="/opt/qiubot/venv/bin/coscmd"

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

# 上传到 COS
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传到 COS..." >> "$LOG"
if $COSCMD upload "$BACKUP" "backups/bazaar_runs.$DATE.db" >> "$LOG" 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] COS 上传成功" >> "$LOG"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] COS 上传失败，本地备份保留" >> "$LOG"
fi

# 本地只保留最近 2 天
find "$BACKUP_DIR" -name 'bazaar_runs.2*.db' -mtime +2 -delete
REMAINING=$(ls "$BACKUP_DIR"/bazaar_runs.2*.db 2>/dev/null | wc -l)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 本地保留备份数: $REMAINING" >> "$LOG"

# COS 只保留最近 3 天的每日备份（bazaar_runs.YYYYMMDD.db）
# 赛季快照（pre_phase_* 等非纯日期命名）永久保留
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清理 COS 旧备份（保留最近3天）..." >> "$LOG"
KEEP_DAYS=3
CUTOFF=$(date -d "-${KEEP_DAYS} days" +%Y%m%d)
COS_LIST=$($COSCMD list backups/ 2>/dev/null)
DELETED=0
while IFS= read -r line; do
    # 只匹配 bazaar_runs.YYYYMMDD.db（纯8位日期，不含下划线后缀）
    FNAME=$(echo "$line" | grep -oP 'bazaar_runs\.\d{8}\.db')
    if [ -z "$FNAME" ]; then continue; fi
    FDATE=$(echo "$FNAME" | grep -oP '\d{8}')
    if [ "$FDATE" -lt "$CUTOFF" ]; then
        $COSCMD delete -f "backups/$FNAME" >> "$LOG" 2>&1 && {
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] COS 已删除: $FNAME" >> "$LOG"
            DELETED=$((DELETED+1))
        }
    fi
done <<< "$COS_LIST"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] COS 清理完成，共删除 $DELETED 个旧备份" >> "$LOG"
