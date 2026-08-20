#!/usr/bin/env python3
import sqlite3, requests, easyocr, numpy as np, logging, time, sys
from PIL import Image
from io import BytesIO
from datetime import datetime

DB_PATH = '/opt/qiubot/data/bazaar_runs.db'
LOG_PATH = '/opt/qiubot/logs/ocr_game_username.log'
BATCH_SIZE = 100
SLEEP_PER_BATCH = 5
HEADERS = {'Referer': 'https://bazaardb.gg/', 'User-Agent': 'Mozilla/5.0'}

import os
os.makedirs('/opt/qiubot/logs', exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s')

reader = easyocr.Reader(['en'], gpu=False, verbose=False)

def extract_username(screenshot_url):
    try:
        full_url = 'https://usercontent.bzdb.network' + screenshot_url
        resp = requests.get(full_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logging.warning(f'下载失败 {screenshot_url}: HTTP {resp.status_code}')
            return None
        img = Image.open(BytesIO(resp.content))
        w, h = img.size
        extra = int(100 * (w * 0.25) / 841)
        crop = img.crop((0, 0, int(w*0.25) + extra, int(h*0.2)))
        cw, ch = crop.size
        sx, sy = cw / (841+100), ch / 404
        uc = crop.crop((int(280*sx), int(150*sy), int(915*sx), int(304*sy)))
        uc = uc.resize((uc.width*3, uc.height*3), Image.LANCZOS)
        result = reader.readtext(np.array(uc))
        text = ''.join([r[1] for r in result]).strip()
        return text or None
    except Exception as e:
        logging.error(f'OCR异常 {screenshot_url}: {e}')
        return None

def run(season, phase, limit=None):
    from datetime import time as dtime
    STOP_HOUR = 6  # 到6点自动停止
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    sql = """SELECT id, screenshot_url FROM runs
             WHERE season=? AND phase=?
             AND screenshot_url IS NOT NULL AND screenshot_url != ''
             AND (game_username IS NULL OR game_username = '')"""
    if limit:
        sql += f' LIMIT {limit}'
    c.execute(sql, (season, phase))
    rows = c.fetchall()
    total = len(rows)
    logging.info(f'开始: Season {season} Phase {phase} 待处理 {total} 条')
    print(f'开始: Season {season} Phase {phase} 待处理 {total} 条')
    ok, fail = 0, 0
    start = datetime.now()
    for idx, (run_id, url) in enumerate(rows, 1):
        username = extract_username(url)
        if username:
            try:
                c.execute('UPDATE runs SET game_username=? WHERE id=?', (username, run_id))
                conn.commit()
                ok += 1
                logging.info(f'[{idx}/{total}] {run_id}: {username}')
            except Exception as e:
                fail += 1
                logging.error(f'[{idx}/{total}] {run_id} 写入失败: {e}')
        else:
            fail += 1
            logging.warning(f'[{idx}/{total}] {run_id} OCR失败: {url}')
        if idx % BATCH_SIZE == 0:
            elapsed = (datetime.now() - start).total_seconds()
            eta = elapsed / idx * (total - idx)
            print(f'进度: {idx}/{total} 成功:{ok} 失败:{fail} 预计剩余:{eta/3600:.1f}h')
            time.sleep(SLEEP_PER_BATCH)
        if datetime.now().hour >= STOP_HOUR:
            msg = f'已到 {STOP_HOUR} 点，本次停止。进度: {idx}/{total} 成功:{ok} 失败:{fail}'
            logging.info(msg)
            print(msg)
            conn.close()
            return
    conn.close()
    summary = f'完成! 总计{total} 成功{ok} 失败{fail}'
    logging.info(summary)
    print(summary)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python ocr_game_username.py <season> <phase> [limit]')
        sys.exit(1)
    run(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
