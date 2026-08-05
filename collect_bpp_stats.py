#!/usr/bin/env python3
"""
BPP 英雄统计每日采集脚本
每天运行一次，从 bpp-metrics.bazaarplusplus.com 拉取英雄统计并存入 SQLite
"""

import sys
import json
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, "/opt/qiubot")
from bpp_client import get_hero_rankings, get_latest_day

DB_PATH = "/opt/qiubot/data/bpp_stats.db"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hero_daily_stats (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT    NOT NULL,
            hero         TEXT    NOT NULL,
            hero_zh      TEXT,
            total_runs   INTEGER,
            ten_win      INTEGER,
            ten_win_rate REAL,
            win_rate     REAL,
            perf_rating  REAL,
            avg_days     REAL,
            perfect      INTEGER,
            gold         INTEGER,
            silver       INTEGER,
            bronze       INTEGER,
            fetched_at   TEXT    NOT NULL,
            UNIQUE(date, hero)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON hero_daily_stats(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hero ON hero_daily_stats(hero)")
    conn.commit()
    return conn


def collect():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始采集 BPP 英雄统计...")

    date = get_latest_day()
    if not date:
        print("  ✗ 无法获取最新日期，退出")
        return

    print(f"  目标日期: {date}")

    try:
        rankings = get_hero_rankings(date)
    except Exception as e:
        print(f"  ✗ 拉取数据失败: {e}")
        return

    if not rankings:
        print("  ✗ 接口返回空数据")
        return

    conn = get_db()
    fetched_at = datetime.now(timezone.utc).isoformat()
    inserted = 0
    skipped = 0

    try:
        for row in rankings:
            try:
                conn.execute(
                    """
                    INSERT INTO hero_daily_stats (
                        date, hero, hero_zh,
                        total_runs, ten_win, ten_win_rate,
                        win_rate, perf_rating, avg_days,
                        perfect, gold, silver, bronze,
                        fetched_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("date", date),
                        row.get("hero", ""),
                        row.get("hero_zh", ""),
                        row.get("total_runs", 0),
                        row.get("ten_win", 0),
                        row.get("ten_win_rate", 0.0),
                        row.get("win_rate", 0.0),
                        row.get("perf_rating", 0.0),
                        row.get("avg_days", 0.0),
                        row.get("perfect", 0),
                        row.get("gold", 0),
                        row.get("silver", 0),
                        row.get("bronze", 0),
                        fetched_at,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1

        conn.commit()
        print(f"  ✓ 日期={date}，新增 {inserted} 条，跳过重复 {skipped} 条，共 {len(rankings)} 位英雄")
    finally:
        conn.close()


if __name__ == "__main__":
    collect()
