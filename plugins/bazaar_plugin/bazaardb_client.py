"""
bazaardb.gg API 客户端
curl_cffi 模拟 Chrome TLS 指纹绕过 Cloudflare，带限速+双层缓存
"""
import json, random, time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests as cf_requests
    HAS_CURL_CFFI = False

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BASE = "https://bazaardb.gg"

_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]
_IMPERSONATE_POOL = ["chrome131", "chrome124", "chrome120", "chrome110", "chrome104"]

_MIN_INTERVAL = 1.5
_last_req_time: float = 0.0
_mem_cache: dict[str, tuple[float, object]] = {}

CARD_CACHE_TTL    = 86400   # 1天
SEARCH_CACHE_TTL  = 600     # 10分钟
PROFILE_CACHE_TTL = 300     # 5分钟


def _get_session():
    if not HAS_CURL_CFFI:
        return cf_requests.Session()
    return cf_requests.Session(impersonate=random.choice(_IMPERSONATE_POOL))


def _headers(referer: str = BASE + "/run") -> dict:
    return {
        "Accept": "application/json, */*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "Origin": BASE,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": random.choice(_UA_POOL),
    }


def _rate_limit():
    global _last_req_time
    wait = _MIN_INTERVAL - (time.time() - _last_req_time) + random.uniform(0.1, 0.9)
    if wait > 0:
        time.sleep(wait)
    _last_req_time = time.time()


def _mem_get(key: str, ttl: float) -> Optional[object]:
    if key in _mem_cache:
        ts, data = _mem_cache[key]
        if time.time() - ts < ttl:
            return data
    return None


def _mem_set(key: str, data: object):
    _mem_cache[key] = (time.time(), data)


def _disk_path(key: str) -> Path:
    safe = key.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
    return CACHE_DIR / f"bazaardb_{safe}.json"


def _disk_get(key: str, ttl: float) -> Optional[object]:
    p = _disk_path(key)
    if p.exists():
        try:
            if time.time() - p.stat().st_mtime < ttl:
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _disk_set(key: str, data: object):
    try:
        _disk_path(key).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _sync_get(path: str, referer: str = BASE + "/run") -> Optional[object]:
    _rate_limit()
    session = _get_session()
    try:
        r = session.get(BASE + path, headers=_headers(referer), timeout=20)
        if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
            return r.json()
        return None
    except Exception as e:
        print(f"[bazaardb] GET {path} 失败: {e}")
        return None
    finally:
        try:
            session.close()
        except Exception:
            pass


# ── 公开 API ──────────────────────────────────────────────────────────────────

def search_cards(query: str, kind: str = "item") -> list[dict]:
    """搜索卡牌。kind: 'item' | 'skill'"""
    key = f"search_{kind}_{query}"
    cached = _mem_get(key, SEARCH_CACHE_TTL)
    if cached is not None:
        return cached
    data = _sync_get(f"/api/search?q={quote(query)}&c={kind}")
    result = data if isinstance(data, list) else []
    _mem_set(key, result)
    return result


def get_card(url_id: str) -> Optional[dict]:
    """按 urlId 获取卡牌完整数据，磁盘缓存1天。"""
    key = f"card_{url_id}"
    cached = _mem_get(key, CARD_CACHE_TTL)
    if cached is not None:
        return cached
    cached = _disk_get(key, CARD_CACHE_TTL)
    if cached is not None:
        _mem_set(key, cached)
        return cached
    data = _sync_get(f"/api/card/{url_id}")
    if isinstance(data, dict) and "Id" in data:
        _mem_set(key, data)
        _disk_set(key, data)
        return data
    return None


def card_link(en_name: str) -> Optional[dict]:
    """按精确英文名查链接，返回 {href, title}。"""
    key = f"cardlink_{en_name}"
    cached = _mem_get(key, CARD_CACHE_TTL)
    if cached is not None:
        return cached
    data = _sync_get(f"/api/card-link?id={quote(en_name)}")
    if isinstance(data, dict) and "href" in data:
        _mem_set(key, data)
        return data
    return None


def search_profile(query: str) -> list[dict]:
    """搜索玩家 profile，返回 [{id, nickname, verified}, ...]。"""
    key = f"profile_{query}"
    cached = _mem_get(key, PROFILE_CACHE_TTL)
    if cached is not None:
        return cached
    data = _sync_get(f"/api/profile-search?q={quote(query)}")
    result = data if isinstance(data, list) else []
    _mem_set(key, result)
    return result


# ── 高层查询（供插件/tool 调用）──────────────────────────────────────────────

def query_card_by_name(name: str) -> Optional[dict]:
    """
    按名字（中/英文）查卡牌，返回完整 card dict。
    流程: 先 card-link 精确匹配 → 搜 item → 搜 skill
    """
    try:
        from . import translations
        if translations.has_chinese(name):
            candidates = translations.search_zh(name, limit=3)
            if candidates:
                name = candidates[0]
    except Exception:
        pass

    # 精确链接
    link = card_link(name)
    if link:
        url_id = link["href"].split("/")[2]
        return get_card(url_id)

    # 模糊搜索
    for kind in ("item", "skill"):
        results = search_cards(name, kind=kind)
        if results:
            return get_card(results[0]["urlId"])

    return None


def format_card_brief(card: dict, zh_name: str = "") -> str:
    """
    把 card dict 格式化为 QQ 消息文本（精简版）。
    """
    from . import translations as trans

    title_en = card.get("Title", {}).get("Text", "") or ""
    title_zh = zh_name or trans.get_zh(title_en) or title_en
    card_type = card.get("Type", "")
    size = card.get("Size", "")
    heroes = ", ".join(card.get("Heroes", [])) or "通用"
    base_tier = card.get("BaseTier", "")
    tags = card.get("DisplayTags", [])
    tags_str = " ".join(f"#{t}" for t in tags) if tags else ""

    lines = []
    type_label = {"Item": "物品", "Skill": "技能"}.get(card_type, card_type)
    size_label = {"Small": "小", "Medium": "中", "Large": "大", "Small Large": "小/大"}.get(size, size)
    lines.append(f"📦 {title_zh}（{title_en}）")
    lines.append(f"类型: {type_label}  尺寸: {size_label}  起始Tier: {base_tier}  英雄: {heroes}")
    if tags_str:
        lines.append(f"标签: {tags_str}")

    # Tooltip（按 tier 展示）
    tiers_data = card.get("Tiers", {})
    tooltips = card.get("Tooltips", [])
    replacements = card.get("TooltipReplacements", {})

    if tooltips:
        lines.append("─")
        for tier_name in ("Bronze", "Silver", "Gold", "Diamond"):
            if tier_name not in tiers_data:
                continue
            tier_lines = []
            for tip in tooltips:
                content = tip.get("Content", {}).get("Text", "") or ""
                if not content:
                    continue
                # 替换占位符
                for placeholder, tier_vals in replacements.items():
                    if isinstance(tier_vals, dict):
                        val = tier_vals.get(tier_name) or tier_vals.get("Fixed")
                    else:
                        val = tier_vals
                    if val is not None:
                        content = content.replace(placeholder, str(val))
                tier_lines.append(content)
            if tier_lines:
                tier_zh = {"Bronze": "铜", "Silver": "银", "Gold": "金", "Diamond": "钻"}.get(tier_name, tier_name)
                lines.append(f"[{tier_zh}] " + " / ".join(tier_lines))

    # 价格
    attrs = card.get("BaseAttributes", {})
    buy = attrs.get("BuyPrice")
    sell = attrs.get("SellPrice")
    if buy or sell:
        lines.append(f"价格: 买{buy}金 / 卖{sell}金")

    # 附魔列表
    enchants = card.get("Enchantments", {})
    if enchants:
        enc_names = list(enchants.keys())
        lines.append(f"附魔: {', '.join(enc_names)}")

    # bazaardb 链接
    uri = card.get("Uri", "")
    if uri:
        lines.append(f"🔗 {BASE}{uri}")

    return "\n".join(lines)

# 别名，供插件调用
format_card = format_card_brief
