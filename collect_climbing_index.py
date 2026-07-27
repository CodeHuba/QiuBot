#!/usr/bin/env python3
"""
爬塔指数水温历史采集脚本
每小时运行一次，从 bazaarapi.mrmao.life 拉取最新数据并存入 SQLite
"""

import sqlite3
import urllib.request
import json
import time
import os
from datetime import datetime

DB_PATH = "/opt/qiubot/data/climbing_index.db"
API_URL = "https://bazaarapi.mrmao.life/api/climbing-index-history"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS climbing_index_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            value REAL NOT NULL,
            created_at INTEGER NOT NULL,
            UNIQUE(timestamp)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON climbing_index_history(timestamp)")
    conn.commit()
    return conn


def parse_timestamp(time_str: str) -> int:
    """将 'MM-DD HH:mm' 格式转换为 Unix 时间戳（使用当前年份）"""
    year = datetime.now().year
    dt = datetime.strptime(f"{year}-{time_str}", "%Y-%m-%d %H:%M")
    return int(dt.timestamp())


def fetch_data():
    req = urllib.request.Request(API_URL, headers={"User-Agent": "QiuBot/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def collect():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始采集...")
    
    try:
        data = fetch_data()
    except Exception as e:
        print(f"  ✗ 请求失败: {e}")
        return

    if not data:
        print("  ✗ 接口返回空数据")
        return

    conn = get_db()
    now = int(time.time())
    inserted = 0
    skipped = 0

    try:
        for item in data:
            ts = parse_timestamp(item["time"])
            try:
                conn.execute(
                    "INSERT INTO climbing_index_history (time, timestamp, value, created_at) VALUES (?, ?, ?, ?)",
                    (item["time"], ts, item["value"], now)
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1  # 已存在，跳过

        conn.commit()
        print(f"  ✓ 新增 {inserted} 条，跳过重复 {skipped} 条，接口共 {len(data)} 条")
    finally:
        conn.close()


if __name__ == "__main__":
    collect()
