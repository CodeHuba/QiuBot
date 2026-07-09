"""
BazaarPlusPlus 数据客户端
从 bpp-metrics.bazaarplusplus.com 获取英雄统计数据
支持本地缓存，减少网络请求
"""
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

BASE_URL = "https://bpp-metrics.bazaarplusplus.com/analyzer-v4"
CACHE_DIR = Path(__file__).parent / "cache" / "bpp"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 英雄名翻译
HERO_ZH = {
    "Pygmalien": "皮格马利翁",
    "Vanessa": "瓦妮莎",
    "Dooley": "杜利",
    "Mak": "马克",
    "Jules": "朱尔斯",
    "Stelle": "斯黛儿",
    "Karnok": "卡诺克",
}


def _cache_path(name: str) -> Path:
    """缓存文件路径"""
    return CACHE_DIR / f"{name}.json"


def _save_cache(name: str, data: dict) -> None:
    """保存数据到缓存"""
    cache = {
        "cached_at": datetime.utcnow().isoformat(),
        "data": data,
    }
    _cache_path(name).write_text(
        json.dumps(cache, ensure_ascii=False), encoding="utf-8"
    )


def _load_cache(name: str, max_age_hours: int = 24) -> Optional[dict]:
    """读取缓存，超过 max_age_hours 小时视为过期"""
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        cache = json.loads(p.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(cache["cached_at"])
        age = datetime.utcnow() - cached_at
        if age.total_seconds() > max_age_hours * 3600:
            return None  # 已过期
        return cache["data"]
    except Exception:
        return None


def _curl_json(url: str, cache_name: Optional[str] = None, max_age_hours: int = 24) -> dict:
    """用 curl 获取 JSON 数据，支持缓存"""
    # 先尝试读缓存
    if cache_name:
        cached = _load_cache(cache_name, max_age_hours)
        if cached is not None:
            return cached
    
    # 缓存未命中，请求网络
    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout)
        
        # 写入缓存
        if cache_name and data:
            _save_cache(cache_name, data)
            print(f"[BPP] 已缓存: {cache_name}")
        
        return data
    except Exception as e:
        print(f"[BPP] 获取数据失败 {url}: {e}")
        # 网络失败时尝试返回过期缓存
        if cache_name:
            cached = _load_cache(cache_name, max_age_hours=999)
            if cached:
                print(f"[BPP] 使用过期缓存: {cache_name}")
                return cached
        return {}


def get_latest_day() -> str:
    """从 manifest 获取最新完整日期（缓存 1 小时）"""
    manifest = _curl_json(f"{BASE_URL}/manifest.json", cache_name="manifest", max_age_hours=1)
    return manifest.get("latest_complete_day", "")


def get_hero_rankings(date: Optional[str] = None) -> list[dict]:
    """
    获取英雄强度排行榜
    
    Returns:
        按10胜率排序的英雄统计列表
    """
    if not date:
        date = get_latest_day()
    if not date:
        return []
    
    # 获取 web 和 ladder 数据（缓存 12 小时）
    web_data = _curl_json(f"{BASE_URL}/web/{date}.json", cache_name=f"web_{date}", max_age_hours=12)
    summary_data = _curl_json(f"{BASE_URL}/ladder/summary.json", cache_name="ladder_summary", max_age_hours=12)
    
    if not web_data or not summary_data:
        return []
    
    # 整合数据（只取 rating_tier=all）
    web_rows = {row['hero']: row for row in web_data.get('rows', []) if row.get('rating_tier') == 'all'}
    ladder_rows = {row['hero']: row for row in summary_data.get('heroes', []) if row.get('rating_tier') == 'all'}
    
    heroes_stats = []
    for hero, wrow in web_rows.items():
        lrow = ladder_rows.get(hero, {})
        runs = wrow.get('runs', {})
        total = runs.get('completed', 0)
        ten_win = runs.get('ten_win', 0)
        ten_win_rate = ten_win / total if total > 0 else 0
        
        twd = wrow.get('ten_win_days', {})
        avg_days = twd.get('sum_days', 0) / twd.get('known_count', 1) if twd.get('known_count', 0) > 0 else 0
        
        win_rate = lrow.get('win_rate', 0)
        perf_rating = lrow.get('perf_rating', 0)
        
        outcomes = wrow.get('outcomes', {})
        perfect = outcomes.get('perfect', 0)
        gold = outcomes.get('gold', 0)
        silver = outcomes.get('silver', 0)
        bronze = outcomes.get('bronze', 0)
        
        heroes_stats.append({
            'hero': hero,
            'hero_zh': HERO_ZH.get(hero, hero),
            'total_runs': total,
            'ten_win': ten_win,
            'ten_win_rate': ten_win_rate,
            'avg_days': avg_days,
            'win_rate': win_rate,
            'perf_rating': perf_rating,
            'perfect': perfect,
            'gold': gold,
            'silver': silver,
            'bronze': bronze,
            'date': date,
        })
    
    # 按10胜率排序
    heroes_stats.sort(key=lambda x: -x['ten_win_rate'])
    return heroes_stats


def get_hero_detail(hero_name: str, date: Optional[str] = None) -> Optional[dict]:
    """
    获取单个英雄的详细统计
    
    Args:
        hero_name: 英雄名（中文或英文）
        date: 日期，默认最新
        
    Returns:
        详细统计数据字典
    """
    if not date:
        date = get_latest_day()
    if not date:
        return None
    
    # 中文转英文
    hero_en = hero_name
    for en, zh in HERO_ZH.items():
        if hero_name == zh or hero_name.lower() == en.lower():
            hero_en = en
            break
    
    # 获取数据（复用缓存）
    web_data = _curl_json(f"{BASE_URL}/web/{date}.json", cache_name=f"web_{date}", max_age_hours=12)
    summary_data = _curl_json(f"{BASE_URL}/ladder/summary.json", cache_name="ladder_summary", max_age_hours=12)
    
    if not web_data or not summary_data:
        return None
    
    # 找到对应英雄的数据（rating_tier=all）
    wrow = None
    for row in web_data.get('rows', []):
        if row.get('hero') == hero_en and row.get('rating_tier') == 'all':
            wrow = row
            break
    
    lrow = None
    for row in summary_data.get('heroes', []):
        if row.get('hero') == hero_en and row.get('rating_tier') == 'all':
            lrow = row
            break
    
    if not wrow:
        return None
    
    # 构建详细数据
    runs = wrow.get('runs', {})
    outcomes = wrow.get('outcomes', {})
    twd = wrow.get('ten_win_days', {})
    battle_days = wrow.get('battle_days', [])
    matchups = wrow.get('matchups', [])
    
    detail = {
        'hero': hero_en,
        'hero_zh': HERO_ZH.get(hero_en, hero_en),
        'date': date,
        'total_runs': runs.get('completed', 0),
        'ten_win': runs.get('ten_win', 0),
        'ten_win_rate': runs.get('ten_win', 0) / runs.get('completed', 1) if runs.get('completed', 0) > 0 else 0,
        'avg_days': twd.get('sum_days', 0) / twd.get('known_count', 1) if twd.get('known_count', 0) > 0 else 0,
        'win_rate': lrow.get('win_rate', 0) if lrow else 0,
        'perf_rating': lrow.get('perf_rating', 0) if lrow else 0,
        'outcomes': {
            'perfect': outcomes.get('perfect', 0),
            'gold': outcomes.get('gold', 0),
            'silver': outcomes.get('silver', 0),
            'bronze': outcomes.get('bronze', 0),
        },
        'battle_days': battle_days,  # [{day, battles, wins, losses}, ...]
        'matchups': matchups,  # [{opponent_hero, decided, wins, losses}, ...]
        'native_rating': lrow.get('native_rating', {}) if lrow else {},
        'native_ranks': lrow.get('native_ranks', []) if lrow else [],
    }
    
    return detail


def refresh_cache() -> dict:
    """
    强制刷新缓存（忽略现有缓存，重新拉取最新数据）
    
    Returns:
        刷新结果 {"success": bool, "date": str, "message": str}
    """
    try:
        # 先删除 manifest 缓存，确保获取最新日期
        manifest_cache = _cache_path("manifest")
        if manifest_cache.exists():
            manifest_cache.unlink()
        
        # 获取最新日期
        date = get_latest_day()
        if not date:
            return {"success": False, "date": "", "message": "无法获取最新日期"}
        
        # 删除旧缓存并重新拉取
        for cache_name in [f"web_{date}", "ladder_summary"]:
            cache_file = _cache_path(cache_name)
            if cache_file.exists():
                cache_file.unlink()
        
        # 强制拉取新数据
        web_data = _curl_json(f"{BASE_URL}/web/{date}.json", cache_name=f"web_{date}", max_age_hours=12)
        summary_data = _curl_json(f"{BASE_URL}/ladder/summary.json", cache_name="ladder_summary", max_age_hours=12)
        
        if not web_data or not summary_data:
            return {"success": False, "date": date, "message": "数据拉取失败"}
        
        return {
            "success": True,
            "date": date,
            "message": f"已更新 {date} 数据"
        }
    except Exception as e:
        return {"success": False, "date": "", "message": f"刷新失败: {str(e)}"}


def cache_status() -> dict:
    """
    查看缓存状态
    
    Returns:
        {"files": [...], "total_size": int}
    """
    files = []
    total_size = 0
    
    for f in CACHE_DIR.glob("*.json"):
        stat = f.stat()
        try:
            cache = json.loads(f.read_text(encoding="utf-8"))
            cached_at = cache.get("cached_at", "未知")
        except Exception:
            cached_at = "损坏"
        
        files.append({
            "name": f.name,
            "size": stat.st_size,
            "cached_at": cached_at,
        })
        total_size += stat.st_size
    
    return {
        "files": files,
        "total_size": total_size,
    }
