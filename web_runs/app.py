"""
BazaarDB Runs 查询 Web API
端口: 1027
"""
import sys
import os
import time
import json
import sqlite3 as _sqlite3
from datetime import datetime
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, send_file, abort

sys.path.insert(0, '/opt/qiubot')
from plugins.bazaar_plugin.runs_query import RunsQuery
from plugins.bazaar_plugin.data_client import CURRENT_SEASON_ID, CURRENT_PHASE

INGEST_TOKEN = '2320869dd20357f336a056abc6b095ea615651ceadabf698'

app = Flask(__name__, static_folder='static')

STATS_DB = '/opt/qiubot/data/query_stats.db'

def _init_stats_db():
    conn = _sqlite3.connect(STATS_DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS query_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_type TEXT,
        params_json TEXT,
        ip TEXT,
        result_count INTEGER,
        success INTEGER,
        created_at TEXT
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ql_type ON query_log(query_type)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ql_time ON query_log(created_at)')
    conn.commit()
    conn.close()

def _log_query(query_type, params, ip, result_count, success):
    try:
        conn = _sqlite3.connect(STATS_DB)
        conn.execute(
            'INSERT INTO query_log (query_type, params_json, ip, result_count, success, created_at) VALUES (?,?,?,?,?,?)',
            (query_type, json.dumps(params, ensure_ascii=False), ip,
             result_count, 1 if success else 0, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

_init_stats_db()

# ===== 限流：同一 IP 3秒内只能查一次 =====
_rate_limit = defaultdict(float)

def rate_limit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        now = time.time()
        last = _rate_limit.get(ip, 0)
        if now - last < 3:
            return jsonify({'error': '查询太频繁，请3秒后再试'}), 429
        _rate_limit[ip] = now
        return f(*args, **kwargs)
    return wrapper


# ===== API 路由 =====

@app.route('/api/runs', methods=['GET'])
@rate_limit
def api_runs():
    hero = request.args.get('hero', '').strip() or None
    cards_raw = request.args.get('cards', '').strip()
    cards = [c.strip() for c in cards_raw.split('+') if c.strip()] or None
    days = request.args.get('days', type=int)
    min_wins = request.args.get('min_wins', default=10, type=int)
    page = request.args.get('page', default=1, type=int)

    try:
        client = RunsQuery()
        client.load()
        if hero:
            resolved = client.resolve_hero(hero)
            if not resolved:
                return jsonify({'error': f'未识别的英雄: {hero}'}), 400
            hero = resolved
        result = client.query(hero=hero, cards=cards, days=days, min_wins=min_wins, page=page)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        _log_query('runs', {'hero': hero, 'cards': cards, 'days': days, 'min_wins': min_wins, 'page': page},
                   ip, result.get('total', 0), True)
        return jsonify(result)
    except Exception as e:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        _log_query('runs', {'hero': hero, 'cards': cards_raw, 'days': days, 'min_wins': min_wins, 'page': page}, ip, 0, False)
        return jsonify({'error': str(e)}), 500


@app.route('/api/winrate', methods=['GET'])
@rate_limit
def api_winrate():
    cards_raw = request.args.get('cards', '').strip()
    cards = [c.strip() for c in cards_raw.split('+') if c.strip()]
    hero_raw = request.args.get('hero', '').strip() or None
    days = request.args.get('days', type=int)

    if not cards:
        return jsonify({'error': '请指定至少一张卡牌'}), 400

    try:
        client = RunsQuery()
        client.load()
        hero = client.resolve_hero(hero_raw) if hero_raw else None
        result = client.winrate(cards=cards, hero=hero, days=days)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        _log_query('winrate', {'cards': cards, 'hero': hero_raw, 'days': days}, ip, result.get('total', 0), True)
        return jsonify(result)
    except Exception as e:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        _log_query('winrate', {'cards': cards_raw, 'hero': hero_raw, 'days': days}, ip, 0, False)
        return jsonify({'error': str(e)}), 500


@app.route('/api/partner', methods=['GET'])
@rate_limit
def api_partner():
    card = request.args.get('card', '').strip()
    days = request.args.get('days', type=int)

    if not card:
        return jsonify({'error': '请指定卡牌名称'}), 400

    try:
        client = RunsQuery()
        client.load()
        result = client.partner(card=card, days=days)
        # 为每个搭档附上图片文件名
        for lst in ('by_winrate', 'by_appear'):
            for p in result.get(lst, []):
                zh = p['name']
                en = client.zh_to_en.get(zh, zh)
                p['img'] = client.tex_map.get(en, '')
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        _log_query('partner', {'card': card, 'days': days}, ip, len(result.get('by_winrate', [])), True)
        return jsonify(result)
    except Exception as e:
        ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        _log_query('partner', {'card': card, 'days': days}, ip, 0, False)
        return jsonify({'error': str(e)}), 500


@app.route('/api/heroes', methods=['GET'])
def api_heroes():
    from plugins.bazaar_plugin.runs_query import HERO_ZH_TO_EN
    heroes = [
        {'zh': zh, 'en': en}
        for zh, en in HERO_ZH_TO_EN.items()
        if zh not in {'海盗', '工程师', '法师', '猪', '机甲', '吸血鬼', '兽人'}  # 去重，只保留官方中文名
    ]
    # 补全标准名
    standard = [
        {'zh': '凡妮莎', 'en': 'Vanessa'},
        {'zh': '杜利',   'en': 'Dooley'},
        {'zh': '马克',   'en': 'Mak'},
        {'zh': '皮格',   'en': 'Pygmalien'},
        {'zh': '斯黛拉', 'en': 'Stelle'},
        {'zh': '朱尔斯', 'en': 'Jules'},
        {'zh': '卡诺克', 'en': 'Karnok'},
    ]
    return jsonify(standard)




@app.route('/api/suggestions')
def api_suggestions():
    try:
        conn = _sqlite3.connect(STATS_DB)
        rows = conn.execute(
            "SELECT params_json, query_type FROM query_log WHERE success=1 ORDER BY id DESC LIMIT 500"
        ).fetchall()
        conn.close()

        from collections import Counter
        hero_counter = Counter()
        card_counter = Counter()

        for params_json, qtype in rows:
            try:
                p = json.loads(params_json)
            except Exception:
                continue
            # 英雄
            hero = p.get('hero')
            if hero:
                hero_map = {'Vanessa':'凡妮莎','Dooley':'杜利','Mak':'马克',
                            'Pygmalien':'皮格','Stelle':'斯黛拉','Jules':'朱尔斯','Karnok':'卡诺克'}
                hero_counter[hero_map.get(hero, hero)] += 1
            # 卡牌
            cards = p.get('cards') or []
            if isinstance(cards, str):
                cards = [cards]
            for c in cards:
                if c:
                    card_counter[c] += 1
            card = p.get('card')
            if card:
                card_counter[card] += 1

        return jsonify({
            'heroes': [{'name': k, 'count': v} for k, v in hero_counter.most_common(7)],
            'cards': [{'name': k, 'count': v} for k, v in card_counter.most_common(10)],
        })
    except Exception as e:
        return jsonify({'heroes': [], 'cards': []}), 200


@app.route('/api/card_img/<path:tex_name>')
def card_img(tex_name):
    img_dir = '/opt/qiubot/plugins/bazaar_plugin/cache/card_images'
    img_path = os.path.join(img_dir, tex_name + '.png')
    if not os.path.exists(img_path):
        abort(404)
    return send_file(img_path, mimetype='image/png')



@app.route('/api/ingest', methods=['POST'])
def api_ingest():
    """采集脚本专用：批量写入 runs 数据"""
    token = request.headers.get('X-Ingest-Token', '')
    if token != INGEST_TOKEN:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True)
    if not data or not isinstance(data, list):
        return jsonify({'error': 'body must be a JSON array'}), 400

    db_path = '/opt/qiubot/data/bazaar_runs.db'
    try:
        conn = __import__('sqlite3').connect(db_path, check_same_thread=False)
        new_count = 0
        for run in data:
            wins = run.get('statWins') or 0
            if wins < 1:
                continue
            try:
                conn.execute("""INSERT OR IGNORE INTO runs
                    (id, hero, username, created_at, items_json, skills_json, combats_json,
                     stat_wins, stat_losses, player_rating, player_rating_after,
                     player_rank, player_rank_after, screenshot_url, raw_json, collected_at, season, phase)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (run['id'], run.get('hero'), run.get('username'),
                     run.get('createdAt'),
                     __import__('json').dumps(run.get('items', []), ensure_ascii=False),
                     __import__('json').dumps(run.get('skills', []), ensure_ascii=False),
                     __import__('json').dumps(run.get('combats', []), ensure_ascii=False),
                     run.get('statWins'), run.get('statLosses'),
                     run.get('playerRating'), run.get('playerRatingAfter'),
                     run.get('playerRank'), run.get('playerRankAfter'),
                     run.get('screenshotUrl'),
                     __import__('json').dumps(run, ensure_ascii=False),
                     __import__('datetime').datetime.now().isoformat(), CURRENT_SEASON_ID, CURRENT_PHASE))
                new_count += conn.total_changes > 0 and 1 or 0
            except Exception as e:
                pass
        conn.commit()
        total = conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0]
        conn.close()
        return jsonify({'ok': True, 'new': new_count, 'total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1027, debug=False)
