"""
BazaarDB Runs 查询模块
支持按英雄、卡牌（中英文）、时间查询，带分页功能
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from . import translations as _trans
from .data_client import CURRENT_SEASON_ID, CURRENT_PHASE


ALIAS_FILE = "/opt/qiubot/data/bz_aliases.json"

# 英雄中英文映射
HERO_ZH_TO_EN = {
    '凡妮莎': 'Vanessa', '海盗': 'Vanessa',
    '杜利': 'Dooley', '工程师': 'Dooley',
    '马克': 'Mak', '法师': 'Mak',
    '皮格': 'Pygmalien', '猪': 'Pygmalien',
    '斯黛拉': 'Stelle', '机甲': 'Stelle',
    '朱尔斯': 'Jules', '吸血鬼': 'Jules',
    '卡诺克': 'Karnok', '兽人': 'Karnok',
    '双龙': 'The Dragons', '龙': 'The Dragons',
}
HERO_EN_SET = {'vanessa', 'dooley', 'mak', 'pygmalien', 'stelle', 'jules', 'karnok', 'the dragons'}


class RunsQuery:
    def __init__(self, db_path: str = "/opt/qiubot/data/bazaar_runs.db",
                 mapping_path: str = "/opt/qiubot/data/card_id_mapping.json",
                 translations_path: str = None):
        self.db_path = db_path
        self.mapping_path = mapping_path
        if translations_path is None:
            translations_path = str(Path(__file__).parent / "cache" / "translations.json")
        self.translations_path = translations_path
        self.conn = None
        self.card_mapping = {}      # cardId -> {name, type}
        self.name_to_ids = {}       # 英文名(lower) -> [cardId]
        self.en_to_zh = {}          # 英文名 -> 中文名
        self.zh_to_en = {}          # 中文名 -> 英文名
        self.card_aliases = {}      # 别名 -> 官方中文名
        self.hero_aliases = {}      # 别名 -> 英雄名
        self.tex_map = {}           # 英文名 -> 图片文件名
        self.card_heroes = {}       # cardId -> [hero list]

    def load(self):
        """加载数据库、映射表和翻译"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        with open(self.mapping_path, 'r', encoding='utf-8') as f:
            self.card_mapping = json.load(f)
        for card_id, info in self.card_mapping.items():
            name = info['name'].lower()
            if name not in self.name_to_ids:
                self.name_to_ids[name] = []
            self.name_to_ids[name].append(card_id)

        # 加载翻译
        trans_path = Path(self.translations_path)
        if trans_path.exists():
            data = json.loads(trans_path.read_text(encoding='utf-8'))
            self.en_to_zh = data
            self.zh_to_en = {v: k for k, v in data.items()}

        # 加载 tex_map
        tex_path = Path(__file__).parent / 'cache' / 'item_tex_map.json'
        if tex_path.exists():
            self.tex_map = json.loads(tex_path.read_text(encoding='utf-8'))

        # 加载卡牌职业映射
        heroes_path = Path('/opt/qiubot/data/card_heroes_map.json')
        if heroes_path.exists():
            self.card_heroes = json.loads(heroes_path.read_text(encoding="utf-8"))

        # 加载自定义别名
        alias_path = Path(ALIAS_FILE)
        if alias_path.exists():
            try:
                raw = json.loads(alias_path.read_text(encoding="utf-8"))
                self.card_aliases = raw.get("cards", {})
                self.hero_aliases = raw.get("heroes", {})
            except Exception:
                pass

    def translate_name(self, name: str) -> str:
        """中文名转英文名，已经是英文则原样返回"""
        if name in self.card_aliases:
            name = self.card_aliases[name]
        if name in self.zh_to_en:
            return self.zh_to_en[name]
        # 模糊匹配中文
        for zh, en in self.zh_to_en.items():
            if name in zh or zh in name:
                return en
        # fallback：社区翻译
        comm = _trans.get_en(name)
        if comm:
            return comm
        results = _trans.search_zh(name, limit=1)
        if results:
            return results[0]
        return name

    def get_zh_name(self, en_name: str) -> str:
        """英文名转中文名，无翻译则返回英文"""
        return self.en_to_zh.get(en_name, en_name)

    def resolve_hero(self, name: str) -> Optional[str]:
        """解析英雄名（支持中英文）"""
        if name in self.hero_aliases:
            name = self.hero_aliases[name]
        if name.lower() in HERO_EN_SET:
            if name.lower() == 'pygmalien':
                return 'Pygmalien'
            if name.lower() == 'the dragons':
                return 'The Dragons'
            return name.capitalize()
        if name in HERO_ZH_TO_EN:
            return HERO_ZH_TO_EN[name]
        return None

    def find_card_ids(self, name: str) -> List[str]:
        """根据卡牌名（支持中英文、模糊匹配）找到 cardId 列表"""
        # 先尝试中文翻译
        en_name = self.translate_name(name)
        name_lower = en_name.lower().replace(' ', '')

        # 精确匹配
        for card_name, ids in self.name_to_ids.items():
            if name_lower == card_name.replace(' ', ''):
                return ids
        # 模糊匹配
        matches = []
        for card_name, ids in self.name_to_ids.items():
            if name_lower in card_name.replace(' ', '') or card_name.replace(' ', '') in name_lower:
                matches.extend(ids)
        return matches

    def query(self,
              hero: Optional[str] = None,
              cards: Optional[List[str]] = None,
              days: Optional[int] = None,
              min_wins: Optional[int] = None,
              page: int = 1,
              page_size: int = 5) -> Dict:
        """
        查询 runs，返回 {runs, total, page, pages, query_desc}
        """
        if not self.conn:
            self.load()

        sql = "SELECT id, hero, username, created_at, items_json, skills_json, stat_wins, stat_losses, screenshot_url FROM runs WHERE season=?"
        params = [CURRENT_SEASON_ID]

        if hero:
            sql += " AND LOWER(hero) = LOWER(?)"
            params.append(hero)
        if days:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            sql += " AND created_at >= ?"
            params.append(cutoff)
        if min_wins:
            sql += " AND stat_wins >= ?"
            params.append(min_wins)

        sql += " ORDER BY created_at DESC"
        rows = self.conn.execute(sql, params).fetchall()

        # 卡牌筛选
        card_ids_sets = []
        if cards:
            for card_name in cards:
                ids = self.find_card_ids(card_name)
                if ids:
                    card_ids_sets.append(set(ids))
                else:
                    return {'runs': [], 'total': 0, 'page': page, 'pages': 0}

        # 过滤
        filtered = []
        for row in rows:
            run_id, hero_name, username, created_at, items_json, skills_json, wins, losses, screenshot = row
            items = json.loads(items_json) if items_json else []
            skills = json.loads(skills_json) if skills_json else []

            run_card_ids = set(it.get('cardId') for it in items if it.get('cardId'))
            run_card_ids.update(sk.get('cardId') for sk in skills if isinstance(sk, dict) and sk.get('cardId'))

            if card_ids_sets:
                if not all(run_card_ids & card_set for card_set in card_ids_sets):
                    continue

            item_names = []
            card_imgs = []
            for it in items:
                cid = it.get('cardId')
                if cid and cid in self.card_mapping:
                    en = self.card_mapping[cid]['name']
                    zh = self.get_zh_name(en)
                    item_names.append(zh)
                    tex = self.tex_map.get(en, '')
                    card_imgs.append(tex)

            screenshot_full = ('https://usercontent.bzdb.network' + screenshot) if screenshot else ''
            filtered.append({
                'id': run_id,
                'hero': hero_name,
                'username': username,
                'created_at': created_at,
                'wins': wins or 0,
                'losses': losses or 0,
                'items': item_names,
                'card_imgs': card_imgs,
                'screenshot': screenshot_full,
                'url': f"https://bazaardb.gg/run/tracker/{run_id}"
            })

        total = len(filtered)
        pages = (total + page_size - 1) // page_size if total > 0 else 0
        page = max(1, min(page, pages)) if pages > 0 else 1

        start = (page - 1) * page_size
        end = start + page_size

        return {
            'runs': filtered[start:end],
            'total': total,
            'page': page,
            'pages': pages
        }

    def format_result(self, result: Dict, query_desc: str = "", raw_cmd: str = "") -> str:
        """格式化查询结果"""
        runs = result['runs']
        total = result['total']
        page = result['page']
        pages = result['pages']

        if not runs:
            return (
                f"未找到符合条件的 runs\n\n"
                f"💡 用法提示：\n"
                f"  #bz runs 海盗 — 按英雄查询\n"
                f"  #bz runs 火炮阵列 — 按卡牌查询\n"
                f"  #bz runs 海盗 赛博铁尺+火炮阵列 — 组合查询\n"
                f"  #bz runs 海盗 --days 3 — 限定时间\n"
                f"  #bz runs 海盗 -p2 — 翻页"
            )

        lines = [f"📋 共 {total} 条结果（第 {page}/{pages} 页）"]
        if query_desc:
            lines[0] += f"  [{query_desc}]"
        lines.append("")

        start_idx = (page - 1) * len(runs)  # approximate
        for i, run in enumerate(runs, start_idx + 1):
            day = run['wins'] + run['losses']
            items_preview = '、'.join(run['items'])

            player = run['username'] or '匿名'
            hero_zh = {'Vanessa': '海盗', 'Dooley': '工程师', 'Mak': '法师',
                       'Pygmalien': '猪', 'Stelle': '机甲', 'Jules': '吸血鬼',
                       'Karnok': '兽人'}.get(run['hero'], run['hero'])

            # 格式化时间
            time_str = ""
            if run.get("created_at"):
                try:
                    from datetime import datetime as _dt
                    dt = _dt.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                    from datetime import timezone, timedelta as _td
                    dt_cn = dt.astimezone(timezone(_td(hours=8)))
                    time_str = dt_cn.strftime("%m-%d %H:%M")
                except Exception:
                    pass

            screenshot_url = ""
            if run.get("screenshot"):
                screenshot_url = run["screenshot"]

            if screenshot_url:
                lines.append(
                    f"{i}. [{hero_zh}] Day{day} {run['wins']}胜{run['losses']}负 | {player} | {time_str}\n"
                    f"[CQ:image,file={screenshot_url}]"
                )
            else:
                lines.append(
                    f"{i}. [{hero_zh}] Day{day} {run['wins']}胜{run['losses']}负 | {player} | {time_str}\n"
                    f"   {items_preview}\n"
                )

        # 翻页提示
        lines.append("")
        if pages > 1:
            if page < pages:
                # 构建翻页命令
                next_cmd = raw_cmd.rstrip() if raw_cmd else "#bz runs"
                # 移除已有的 -p 参数
                import re
                next_cmd = re.sub(r'\s*-p\d+', '', next_cmd)
                lines.append(f"▶ 下一页: {next_cmd} -p{page+1}")
            if page > 1:
                prev_cmd = raw_cmd.rstrip() if raw_cmd else "#bz runs"
                import re
                prev_cmd = re.sub(r'\s*-p\d+', '', prev_cmd)
                lines.append(f"◀ 上一页: {prev_cmd} -p{page-1}")

        # 用法提示
        lines.append("")
        lines.append("💡 #bz runs [英雄] [卡牌+卡牌] [--days N] [-pN]")

        return '\n'.join(lines)


    def winrate(self,
                cards: list,
                hero: str = None,
                days: int = None,
                min_wins_threshold: int = 10,
                all_phases: bool = False) -> dict:
        """
        计算包含指定卡牌组合的 runs 中，达到 min_wins_threshold 胜的比率。
        返回 {total, ten_win, rate, card_names, not_found}
        """
        import json as _json
        from datetime import datetime as _dt, timedelta as _td

        if not self.conn:
            self.load()

        # 解析卡牌 -> cardId 集合
        card_ids_sets = []
        not_found = []
        card_names = []
        for card_name in cards:
            ids = self.find_card_ids(card_name)
            if not ids:
                not_found.append(card_name)
            else:
                card_ids_sets.append(set(ids))
                en_name = self.translate_name(card_name)
                zh = self.get_zh_name(en_name)
                card_names.append(zh if zh != en_name else card_name)

        if not card_ids_sets:
            return {'total': 0, 'ten_win': 0, 'rate': 0.0,
                    'card_names': card_names, 'not_found': not_found}

        # 拉取所有 runs（按条件过滤英雄/时间/阶段）
        sql = "SELECT items_json, stat_wins FROM runs WHERE season=?"
        params = [CURRENT_SEASON_ID]
        if not all_phases:
            sql += " AND phase=?"
            params.append(CURRENT_PHASE)
        if hero:
            sql += " AND LOWER(hero) = LOWER(?)"
            params.append(hero)
        if days:
            cutoff = (_dt.utcnow() - _td(days=days)).isoformat()
            sql += " AND created_at >= ?"
            params.append(cutoff)
        rows = self.conn.execute(sql, params).fetchall()

        total = 0
        ten_win = 0
        for items_json, wins in rows:
            try:
                items = _json.loads(items_json)
                run_card_ids = {item['cardId'] for item in items if 'cardId' in item}
            except Exception:
                continue
            # 检查是否包含所有指定卡牌组合（每组卡牌取交集）
            if all(run_card_ids & id_set for id_set in card_ids_sets):
                total += 1
                if (wins or 0) >= min_wins_threshold:
                    ten_win += 1

        rate = ten_win / total if total > 0 else 0.0
        return {
            'total': total,
            'ten_win': ten_win,
            'rate': rate,
            'card_names': card_names,
            'not_found': not_found,
        }


    def partner(self,
                card: str,
                days: int = None,
                min_count: int = 50,
                top_n: int = 3,
                wins_threshold: int = 10,
                all_phases: bool = False) -> dict:
        """
        查询与某张卡搭配时胜率最高的前 top_n 张搭档卡。
        只统计出现次数 >= min_count 的搭档。
        返回 {card_name, partners: [{name, total, ten_win, rate}], not_found}
        """
        import json as _json
        from datetime import datetime as _dt, timedelta as _td
        from collections import defaultdict

        if not self.conn:
            self.load()

        # 解析目标卡
        ids = self.find_card_ids(card)
        if not ids:
            return {"card_name": card, "partners": [], "not_found": True}
        target_ids = set(ids)
        en_name = self.translate_name(card)
        card_name = self.get_zh_name(en_name)
        if card_name == en_name:
            card_name = card

        # 拉取所有 runs（按条件过滤阶段/时间）
        sql = "SELECT items_json, stat_wins FROM runs WHERE season=?"
        params = [CURRENT_SEASON_ID]
        if not all_phases:
            sql += " AND phase=?"
            params.append(CURRENT_PHASE)
        if days:
            cutoff = (_dt.utcnow() - _td(days=days)).isoformat()
            sql += " AND created_at >= ?"
            params.append(cutoff)
        rows = self.conn.execute(sql, params).fetchall()

        # 统计每张搭档卡的出现次数和10胜次数
        total_map = defaultdict(int)
        win_map = defaultdict(int)

        for items_json, wins in rows:
            try:
                items = _json.loads(items_json)
                run_ids = {item["cardId"] for item in items if "cardId" in item}
            except Exception:
                continue
            # 该局必须包含目标卡
            if not (run_ids & target_ids):
                continue
            is_win = (wins or 0) >= wins_threshold
            # 统计搭档（排除目标卡自身）
            for cid in run_ids:
                if cid in target_ids:
                    continue
                total_map[cid] += 1
                if is_win:
                    win_map[cid] += 1

        # 过滤低样本，计算胜率，排序
        results = []
        for cid, total in total_map.items():
            if total < min_count:
                continue
            ten_win = win_map.get(cid, 0)
            rate = ten_win / total
            # 获取卡牌名
            info = self.card_mapping.get(cid, {})
            en = info.get("name", "")
            if not en:
                continue  # 跳过不在 mapping 里的卡
            zh = self.get_zh_name(en)
            name = zh if zh != en else en
            results.append({"name": name, "total": total, "ten_win": ten_win, "rate": rate})

        # 计算共现率（含目标卡的局里，搭档出现的比例）
        target_total = sum(1 for items_json, wins in rows
                          if (lambda ids: bool(ids & target_ids))(
                              {item['cardId'] for item in __import__('json').loads(items_json) if 'cardId' in item}))

        for r in results:
            cid_list = [cid for cid, info in self.card_mapping.items()
                        if (info.get('name','') == (self.en_to_zh.get(r['name'], r['name']) or r['name'])
                            or self.get_zh_name(info.get('name','')) == r['name'])]
            r['appear_rate'] = r['total'] / target_total if target_total > 0 else 0

        by_winrate = sorted(results, key=lambda x: (-x['rate'], -x['total']))[:top_n]
        by_appear = sorted(results, key=lambda x: (-x['appear_rate'], -x['total']))[:top_n]

        return {
            'card_name': card_name,
            'by_winrate': by_winrate,
            'by_appear': by_appear,
            'target_total': target_total,
            'not_found': False,
        }



    def topcard(self,
                hero: str,
                top_n: int = 5,
                days: int = None,
                min_count: int = 50,
                all_phases: bool = False) -> dict:
        """
        查询某个职业下胜率最高的 top_n 张物品卡（只统计该职业专属卡）。
        统计该职业所有 runs 中每张卡的出现次数、胜场数（stat_wins >= 10）、胜率。
        返回 {hero, hero_zh, top: [{name_zh, name_en, total, ten_win, rate}], total_runs, days}
        """
        import json as _json
        from datetime import datetime as _dt, timedelta as _td

        if not self.conn:
            self.load()

        # 拉取该英雄所有 runs（按条件过滤阶段/时间）
        sql = "SELECT items_json, stat_wins FROM runs WHERE season=? AND LOWER(hero)=LOWER(?)"
        params = [CURRENT_SEASON_ID, hero]
        if not all_phases:
            sql += " AND phase=?"
            params.append(CURRENT_PHASE)
        if days:
            cutoff = (_dt.utcnow() - _td(days=days)).isoformat()
            sql += " AND created_at >= ?"
            params.append(cutoff)
        rows = self.conn.execute(sql, params).fetchall()

        # 统计每张卡的出现次数和胜场数（只统计该职业专属卡）
        card_total: dict = {}   # cardId -> total count
        card_wins: dict = {}    # cardId -> 10win count

        # GameData.db 中双龙的职业名为 Hero8
        _hero_gamedata = {'The Dragons': 'Hero8'}.get(hero, hero)

        for items_json, wins in rows:
            try:
                items = _json.loads(items_json)
                run_ids = {item['cardId'] for item in items if 'cardId' in item}
            except Exception:
                continue
            is_win = (wins or 0) >= 10
            for cid in run_ids:
                # 过滤：只统计该职业专属卡
                card_heroes_list = self.card_heroes.get(cid, [])
                if _hero_gamedata not in card_heroes_list:
                    continue
                card_total[cid] = card_total.get(cid, 0) + 1
                if is_win:
                    card_wins[cid] = card_wins.get(cid, 0) + 1

        # 过滤低频卡，计算胜率
        results = []
        for cid, total in card_total.items():
            if total < min_count:
                continue
            info = self.card_mapping.get(cid, {})
            name_en = info.get('name', cid)
            name_zh = self.get_zh_name(name_en)
            ten_win = card_wins.get(cid, 0)
            rate = ten_win / total if total > 0 else 0.0
            results.append({
                'name_zh': name_zh if name_zh != name_en else name_en,
                'name_en': name_en,
                'total': total,
                'ten_win': ten_win,
                'rate': rate,
            })

        results.sort(key=lambda x: (-x['rate'], -x['total']))
        top = results[:top_n]

        hero_map = {'Vanessa': '海盗/凡妮莎', 'Dooley': '工程师/杜利',
                    'Mak': '法师/马克', 'Pygmalien': '猪/皮格',
                    'Stelle': '机甲/斯黛拉', 'Jules': '吸血鬼/朱尔斯',
                    'Karnok': '兽人/卡诺克', 'The Dragons': '双龙'}
        hero_zh = hero_map.get(hero, hero)

        return {
            'hero': hero,
            'hero_zh': hero_zh,
            'top': top,
            'total_runs': len(rows),
            'days': days,
        }
_client = None

def get_client() -> RunsQuery:
    global _client
    if _client is None:
        _client = RunsQuery()
        _client.load()
    return _client
