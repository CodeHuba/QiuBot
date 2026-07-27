#!/usr/bin/env python3
"""
赛季结束清库脚本
用法: python3 clear_season.py [--confirm]
"""
import sqlite3
import os
import sys
import shutil
from datetime import datetime

DB_PATH = '/opt/qiubot/data/bazaar_runs.db'

conn = sqlite3.connect(DB_PATH)
total = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
oldest = conn.execute("SELECT MIN(created_at) FROM runs").fetchone()[0]
newest = conn.execute("SELECT MAX(created_at) FROM runs").fetchone()[0]
conn.close()

print(f"当前数据库: {total} 条 runs")
print(f"时间范围: {oldest} ~ {newest}")
print(f"文件大小: {os.path.getsize(DB_PATH) // 1024 // 1024} MB")

if '--confirm' not in sys.argv:
    print("\n⚠️  这将清空所有 runs 数据！")
    print("确认清库请加 --confirm 参数:")
    print("  python3 clear_season.py --confirm")
    sys.exit(0)

# 备份
backup_path = DB_PATH + f'.bak.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
shutil.copy2(DB_PATH, backup_path)
print(f"\n✅ 已备份到: {backup_path}")

# 清空
conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM runs")
conn.execute("VACUUM")
conn.commit()
conn.close()

print(f"✅ 已清空 {total} 条 runs，新赛季可以重新采集了")
