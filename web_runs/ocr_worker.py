"""
OCR Worker 模块：后台线程处理新 runs 的游戏用户名识别
"""
import queue
import threading
import time
import logging
import requests
import numpy as np
from PIL import Image
from io import BytesIO
import sqlite3

# 全局队列和 reader（延迟初始化）
ocr_queue = queue.Queue(maxsize=1000)
reader = None
worker_thread = None

HEADERS = {'Referer': 'https://bazaardb.gg/', 'User-Agent': 'Mozilla/5.0'}
DB_PATH = '/opt/qiubot/data/bazaar_runs.db'
LOG_PATH = '/opt/qiubot/logs/ocr_worker.log'

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)


def extract_username(screenshot_url):
    """从截图 OCR 识别用户名"""
    global reader
    
    # 延迟加载 EasyOCR（首次调用时初始化）
    if reader is None:
        import easyocr
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        logging.info('EasyOCR 初始化完成')
    
    try:
        full_url = 'https://usercontent.bzdb.network' + screenshot_url
        resp = requests.get(full_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
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
        logging.error(f'OCR 失败 {screenshot_url}: {e}')
        return None


def ocr_worker():
    """后台线程：消费队列，OCR 识别并写入数据库"""
    logging.info('OCR worker 启动')
    
    while True:
        try:
            # 阻塞等待任务（超时 10 秒检查一次）
            try:
                run_id, screenshot_url = ocr_queue.get(timeout=10)
            except queue.Empty:
                continue
            
            # OCR 识别
            username = extract_username(screenshot_url)
            
            # 写入数据库
            if username:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute('UPDATE runs SET game_username=? WHERE id=?', (username, run_id))
                    conn.commit()
                    conn.close()
                    logging.info(f'{run_id}: {username}')
                except Exception as e:
                    logging.error(f'{run_id} 写入失败: {e}')
            else:
                logging.warning(f'{run_id} OCR 失败')
            
            # 标记任务完成
            ocr_queue.task_done()
            
            # 限速：每条休息 0.5 秒，避免打满 CPU
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f'Worker 异常: {e}')
            time.sleep(1)


def start_worker():
    """启动后台 OCR 线程"""
    global worker_thread
    if worker_thread is None or not worker_thread.is_alive():
        worker_thread = threading.Thread(target=ocr_worker, daemon=True, name='OCR-Worker')
        worker_thread.start()
        logging.info('OCR worker 线程已启动')


def enqueue_run(run_id, screenshot_url):
    """将新 run 加入 OCR 队列"""
    if not screenshot_url:
        return
    try:
        ocr_queue.put_nowait((run_id, screenshot_url))
    except queue.Full:
        logging.warning(f'OCR 队列已满，跳过 {run_id}')
