#!/bin/bash
# 赛季/补丁更新 SOP 脚本
# 用法:
#   补丁更新: ./season_update.sh patch 17.4
#   大赛季更新: ./season_update.sh season 18 18.1 "2026-08-16 16:00:00"
#     最后一个参数是赛季开始的北京时间，用于修正误打标签的 runs

set -e

QIUBOT_ROOT="/opt/qiubot"
DATA_CLIENT="$QIUBOT_ROOT/plugins/bazaar_plugin/data_client.py"
FETCH_IMAGES="$QIUBOT_ROOT/tools/fetch_card_images.py"
README_IMAGES="$QIUBOT_ROOT/tools/README_card_images.md"
GAMEDATA_DB="$QIUBOT_ROOT/plugins/bazaar_plugin/cache/GameData.db"
ZH_CN_BYTES="$QIUBOT_ROOT/AppData/LocalLow/Tempo Storm/The Bazaar/prod/cache/translations/zh-CN.bytes"
RUNS_DB="$QIUBOT_ROOT/data/bazaar_runs.db"
UPLOAD_DIR="/home/ubuntu"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 检查参数
if [ $# -lt 2 ]; then
    echo "用法:"
    echo "  补丁更新: $0 patch <new_phase> <patch_release_time>"
    echo "    示例: $0 patch 17.4 \"2026-08-21 10:00:00\""
    echo "    最后一个参数是北京时间，用于修正 runs 数据库中的 phase"
    echo ""
    echo "  大赛季更新: $0 season <new_season_id> <new_phase> <season_start_time>"
    echo "    示例: $0 season 18 18.1 \"2026-08-16 16:00:00\""
    echo "    最后一个参数是北京时间，用于修正 runs 数据库中误标的赛季号和 phase"
    exit 1
fi

UPDATE_TYPE=$1

if [ "$UPDATE_TYPE" = "patch" ]; then
    NEW_PHASE=$2
    PATCH_RELEASE_BJ=$3
    
    if [ -z "$PATCH_RELEASE_BJ" ]; then
        log_error "补丁更新需要提供 <new_phase> 和 <patch_release_time>"
    fi
    
    log_info "补丁更新模式: 新阶段 = $NEW_PHASE"
    log_info "补丁发布时间(北京): $PATCH_RELEASE_BJ"
    
    # 北京时间转 UTC
    RELEASE_TIME_UTC=$(python3 -c "from datetime import datetime, timedelta; bj=datetime.strptime('$PATCH_RELEASE_BJ', '%Y-%m-%d %H:%M:%S'); utc=bj-timedelta(hours=8); print(utc.strftime('%Y-%m-%dT%H:%M:%S'))")
    log_info "补丁发布时间(UTC): $RELEASE_TIME_UTC"
    
    # 读取当前值
    CURRENT_SEASON_ID=$(grep -oP 'CURRENT_SEASON_ID = \K\d+' "$DATA_CLIENT")
    RUNS_SEASON_ID=$(grep -oP 'RUNS_SEASON_ID = \K\d+' "$DATA_CLIENT")
    OLD_PHASE=$(grep -oP 'CURRENT_PHASE = "\K[^"]+' "$DATA_CLIENT")
    
    log_info "保持 CURRENT_SEASON_ID = $CURRENT_SEASON_ID"
    log_info "保持 RUNS_SEASON_ID = $RUNS_SEASON_ID"
    log_info "PHASE: $OLD_PHASE → $NEW_PHASE"
    
elif [ "$UPDATE_TYPE" = "season" ]; then
    NEW_SEASON_ID=$2
    NEW_PHASE=$3
    SEASON_START_BJ=$4
    
    if [ -z "$NEW_PHASE" ] || [ -z "$SEASON_START_BJ" ]; then
        log_error "大赛季更新需要提供 <new_season_id> <new_phase> <season_start_time>"
    fi
    
    log_info "大赛季更新模式: 新赛季 = $NEW_SEASON_ID, 新阶段 = $NEW_PHASE"
    log_info "赛季开始时间(北京): $SEASON_START_BJ"
    
    # 北京时间转 UTC (用 Python，避免服务器时区问题)
    SEASON_START_UTC=$(python3 -c "from datetime import datetime, timedelta; bj=datetime.strptime('$SEASON_START_BJ', '%Y-%m-%d %H:%M:%S'); utc=bj-timedelta(hours=8); print(utc.strftime('%Y-%m-%dT%H:%M:%S'))")
    log_info "赛季开始时间(UTC): $SEASON_START_UTC"
    
    # 大赛季更新时，RUNS_SEASON_ID = 上一个赛季号
    RUNS_SEASON_ID=$((NEW_SEASON_ID - 1))
    CURRENT_SEASON_ID=$NEW_SEASON_ID
    
    log_info "CURRENT_SEASON_ID = $CURRENT_SEASON_ID"
    log_info "RUNS_SEASON_ID = $RUNS_SEASON_ID (采集脚本仍在收集上赛季数据)"
    
else
    log_error "未知的更新类型: $UPDATE_TYPE (应为 patch 或 season)"
fi

# ========== 1. 检查上传文件 ==========
log_info "Step 1: 检查上传文件"
if [ ! -f "$UPLOAD_DIR/GameData.db" ]; then
    log_error "未找到 $UPLOAD_DIR/GameData.db，请先上传"
fi
if [ ! -f "$UPLOAD_DIR/zh-CN.bytes" ]; then
    log_error "未找到 $UPLOAD_DIR/zh-CN.bytes，请先上传"
fi
log_info "✓ 文件检查通过"

# ========== 2. 备份旧文件 ==========
log_info "Step 2: 备份旧文件"
BACKUP_DIR="$QIUBOT_ROOT/backups/season_update_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp "$DATA_CLIENT" "$BACKUP_DIR/"
cp "$GAMEDATA_DB" "$BACKUP_DIR/"
cp "$ZH_CN_BYTES" "$BACKUP_DIR/"
log_info "✓ 备份完成: $BACKUP_DIR"

# ========== 3. 替换 GameData.db 和 zh-CN.bytes ==========
log_info "Step 3: 替换 GameData.db 和 zh-CN.bytes"
cp "$UPLOAD_DIR/GameData.db" "$GAMEDATA_DB"
cp "$UPLOAD_DIR/zh-CN.bytes" "$ZH_CN_BYTES"
log_info "✓ 数据库文件替换完成"

# ========== 3.5 修正 runs 数据库的 season 和 phase ==========
log_info "Step 3.5: 检查并修正 runs 数据库"

if [ "$UPDATE_TYPE" = "patch" ]; then
    CUTOFF_UTC="$RELEASE_TIME_UTC"
    FIX_SEASON=0
elif [ "$UPDATE_TYPE" = "season" ]; then
    CUTOFF_UTC="$SEASON_START_UTC"
    FIX_SEASON=1
fi

FIX_RESULT=$(python3 << PYEOF
import sqlite3

db = "$RUNS_DB"
fix_season = $FIX_SEASON
old_season = $RUNS_SEASON_ID
new_season = $CURRENT_SEASON_ID
new_phase = "$NEW_PHASE"
cutoff_utc = "$CUTOFF_UTC"

conn = sqlite3.connect(db)

if fix_season:
    # 大赛季：同时修正 season 和 phase
    count = conn.execute(
        "SELECT COUNT(*) FROM runs WHERE season=? AND created_at >= ?",
        (old_season, cutoff_utc)
    ).fetchone()[0]
    if count > 0:
        conn.execute(
            "UPDATE runs SET season=?, phase=? WHERE season=? AND created_at >= ?",
            (new_season, new_phase, old_season, cutoff_utc)
        )
else:
    # 补丁：只修正 phase（season 不变）
    count = conn.execute(
        "SELECT COUNT(*) FROM runs WHERE season=? AND created_at >= ?",
        (old_season, cutoff_utc)
    ).fetchone()[0]
    if count > 0:
        conn.execute(
            "UPDATE runs SET phase=? WHERE season=? AND created_at >= ?",
            (new_phase, old_season, cutoff_utc)
        )

if count > 0:
    conn.commit()

print(f"FIXED:{count}")
conn.close()
PYEOF
)

FIX_COUNT=$(echo "$FIX_RESULT" | grep -oP 'FIXED:\K\d+')
if [ "$FIX_COUNT" -gt 0 ]; then
    if [ "$FIX_SEASON" = "1" ]; then
        log_info "✓ 已修正 $FIX_COUNT 条 runs: season S$RUNS_SEASON_ID→S$CURRENT_SEASON_ID, phase→$NEW_PHASE"
    else
        log_info "✓ 已修正 $FIX_COUNT 条 runs: phase→$NEW_PHASE"
    fi
else
    log_info "✓ 无需修正（时间点之后无误标数据）"
fi

# ========== 4. 更新 data_client.py ==========
log_info "Step 4: 更新 data_client.py"
if [ "$UPDATE_TYPE" = "season" ]; then
    sed -i "s/^CURRENT_SEASON_ID = .*/CURRENT_SEASON_ID = $CURRENT_SEASON_ID/" "$DATA_CLIENT"
    sed -i "s/^RUNS_SEASON_ID = .*/RUNS_SEASON_ID = $RUNS_SEASON_ID/" "$DATA_CLIENT"
fi
sed -i "s/^CURRENT_PHASE = .*/CURRENT_PHASE = \"$NEW_PHASE\"  # 当前赛季阶段，补丁后手动更新/" "$DATA_CLIENT"
log_info "✓ data_client.py 已更新"

# ========== 5. 更新 fetch_card_images.py ==========
log_info "Step 5: 更新 fetch_card_images.py"
sed -i "s/'version': '[^']*'/'version': '$NEW_PHASE'/" "$FETCH_IMAGES"
log_info "✓ fetch_card_images.py 已更新"

# ========== 6. 更新 README_card_images.md ==========
log_info "Step 6: 更新 README_card_images.md"
if [ -f "$README_IMAGES" ]; then
    # README 里是 JSON 格式: "version": "17.3"
    sed -i "s/\"version\": \"[0-9.]*\"/\"version\": \"$NEW_PHASE\"/" "$README_IMAGES"
    log_info "✓ README_card_images.md 已更新"
else
    log_warn "未找到 $README_IMAGES，跳过"
fi

# ========== 7. 清理 pyc 缓存 ==========
log_info "Step 7: 清理 Python 缓存"
find "$QIUBOT_ROOT/plugins/bazaar_plugin" -name '*.pyc' -delete
find "$QIUBOT_ROOT/web_runs" -name '*.pyc' -delete
log_info "✓ pyc 缓存已清理"

# ========== 8. 重启 web_runs 服务 ==========
log_info "Step 8: 重启 web_runs 服务"
pkill -f 'python.*app.py' || true
sleep 2
cd "$QIUBOT_ROOT/web_runs"
nohup ../venv/bin/python app.py >> logs/app.log 2>&1 &
sleep 3
log_info "✓ web_runs 服务已重启"

# ========== 9. 验证接口 ==========
log_info "Step 9: 验证接口"
RESPONSE=$(curl -s 'http://localhost:1027/api/runs?hero=Vanessa&min_wins=10&rank=all')
TOTAL=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('total', 0))")
if [ "$TOTAL" -gt 0 ]; then
    log_info "✓ 接口验证通过: total = $TOTAL"
else
    log_warn "接口返回 total = 0，请检查日志"
fi

# ========== 10. Git 提交 ==========
log_info "Step 10: Git 提交"
cd "$QIUBOT_ROOT"
git add plugins/bazaar_plugin/data_client.py tools/fetch_card_images.py docs/README_card_images.md 2>/dev/null || true
if [ "$UPDATE_TYPE" = "season" ]; then
    COMMIT_MSG="chore: 赛季更新 S$NEW_SEASON_ID ($NEW_PHASE)"
else
    COMMIT_MSG="chore: 补丁更新 $NEW_PHASE"
fi
git commit -m "$COMMIT_MSG" || log_warn "无新改动需要提交"
log_info "✓ Git 提交完成"

# ========== 11. 提示后续操作 ==========
echo ""
log_info "========== 更新完成 =========="
log_info "当前配置:"
log_info "  CURRENT_SEASON_ID = $(grep -oP 'CURRENT_SEASON_ID = \K\d+' $DATA_CLIENT)"
log_info "  CURRENT_PHASE = $(grep -oP 'CURRENT_PHASE = \"\K[^\"]+' $DATA_CLIENT)"
log_info "  RUNS_SEASON_ID = $(grep -oP 'RUNS_SEASON_ID = \K\d+' $DATA_CLIENT)"
echo ""
log_warn "后续手动操作:"
log_warn "  1. 推送 Git: cd $QIUBOT_ROOT && git push origin main"
if [ "$UPDATE_TYPE" = "season" ]; then
    log_warn "  2. 更新 Windows 采集脚本的 SEASON_START (D:\\PJ\\QiuBot\\tools\\bazaardb_runs_collector.py)"
fi
log_warn "  3. 重新拉取卡牌图片: cd $QIUBOT_ROOT/tools && ../venv/bin/python fetch_card_images.py"
log_warn "  4. 清理上传目录: rm $UPLOAD_DIR/GameData.db $UPLOAD_DIR/zh-CN.bytes"
echo ""
