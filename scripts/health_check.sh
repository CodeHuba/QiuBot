#!/bin/bash
# 健康检查：web_runs 服务和 qiubot 主服务
# 退出码 0=正常（静默），非0=异常（输出告警信息）

LOG="/opt/qiubot/logs/health_check.log"
ALERT=""

# 检查 1027 端口 HTTP 服务
if ! curl -sf --max-time 5 http://localhost:1027/api/heroes > /dev/null 2>&1; then
    ALERT="${ALERT}web_runs port 1027 无响应\n"
fi

# 检查 qiubot systemd 服务
if ! systemctl is-active --quiet qiubot; then
    ALERT="${ALERT}qiubot systemd 服务未运行\n"
fi

# 检查数据库文件可访问性
if [ ! -r /opt/qiubot/data/bazaar_runs.db ]; then
    ALERT="${ALERT}bazaar_runs.db 不可读\n"
fi

# 检查磁盘使用率 (>90% 告警)
DISK_USAGE=$(df /data0809 | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    ALERT="${ALERT}/data0809 磁盘使用率 ${DISK_USAGE}%\n"
fi

if [ -n "$ALERT" ]; then
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] 健康检查失败:\n${ALERT}" | tee -a "$LOG"
    exit 1
else
    # 正常时静默（no_agent=True 的 cronjob 空输出不会推送消息）
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] OK" >> "$LOG"
    exit 0
fi
