"""
英文 → 中文翻译表
- 官方翻译 (translations.json): 英文名 → 官方中文名 (来自 zh-CN.bytes + cards.json)
- 社区翻译 (translations_community.json): 英文名 → 社区中文名 (来自 bazaardb.gg)
搜索时两套都能匹配，官方翻译优先展示。
"""
import json
from pathlib import Path

CACHE_DIR        = Path(__file__).parent / "cache"
TRANS_FILE       = CACHE_DIR / "translations.json"
TRANS_COMM_FILE  = CACHE_DIR / "translations_community.json"

# 官方: en→zh_official, zh_official→en
_official_en_to_zh: dict[str, str] = {}
_official_zh_to_en: dict[str, str] = {}
_official_en_lower: dict[str, str] = {}

# 社区: en→zh_community, zh_community→en
_comm_en_to_zh: dict[str, str] = {}
_comm_zh_to_en: dict[str, str] = {}

# 合并反查: 任意中文→英文 (官方+社区)
_any_zh_to_en: dict[str, str] = {}


def _load():
    global _official_en_to_zh, _official_zh_to_en, _official_en_lower
    global _comm_en_to_zh, _comm_zh_to_en, _any_zh_to_en

    # 官方翻译
    if TRANS_FILE.exists():
        try:
            data = json.loads(TRANS_FILE.read_text(encoding="utf-8"))
            _official_en_to_zh = data
            _official_zh_to_en = {zh: en for en, zh in data.items()}
            _official_en_lower = {en.lower(): zh for en, zh in data.items()}
            print(f"[translations] 官方翻译: {len(_official_en_to_zh)} 条")
        except Exception as e:
            print(f"[translations] 官方翻译加载失败: {e}")

    # 社区翻译
    if TRANS_COMM_FILE.exists():
        try:
            data = json.loads(TRANS_COMM_FILE.read_text(encoding="utf-8"))
            _comm_en_to_zh = data
            _comm_zh_to_en = {zh: en for en, zh in data.items()}
            print(f"[translations] 社区翻译: {len(_comm_en_to_zh)} 条")
        except Exception as e:
            print(f"[translations] 社区翻译加载失败: {e}")

    # 合并反查: 官方先放，社区覆盖（社区优先）
    _any_zh_to_en = {}
    _any_zh_to_en.update(_official_zh_to_en)
    _any_zh_to_en.update(_comm_zh_to_en)


_load()


def _preload_community_from_cache():
    """启动时从 bazaardb 磁盘缓存批量注册社区翻译"""
    import json
    cache_dir = CACHE_DIR
    count = 0
    try:
        for f in cache_dir.glob("bazaardb_card_*.json"):
            try:
                card = json.loads(f.read_text(encoding="utf-8"))
                en = card.get("_originalTitleText", "")
                zh = (card.get("Title") or {}).get("Text", "")
                if en and zh and has_chinese(zh) and en != zh:
                    register_community(en, zh)
                    count += 1
            except Exception:
                pass
    except Exception:
        pass
    if count:
        print(f"[translations] 社区翻译(缓存预热): {count} 条")




def get_zh(name_en: str) -> str | None:
    """英文名 → 中文名（社区优先，无社区则返回官方）"""
    if not name_en:
        return None
    result = _comm_en_to_zh.get(name_en)
    if result:
        return result
    return _official_en_to_zh.get(name_en) or _official_en_lower.get(name_en.lower())


def get_zh_both(name_en: str) -> tuple[str | None, str | None]:
    """返回 (官方中文, 社区中文)，无则 None"""
    if not name_en:
        return None, None
    off = _official_en_to_zh.get(name_en) or _official_en_lower.get(name_en.lower())
    com = _comm_en_to_zh.get(name_en)
    return off, com


def get_en(name_zh: str) -> str | None:
    """中文名 → 英文名（官方+社区都能匹配）"""
    if not name_zh:
        return None
    return _any_zh_to_en.get(name_zh.strip())


def search_zh(query: str, limit: int = 10) -> list[str]:
    """中文模糊查询，返回英文名列表（官方+社区两套都搜，短的优先）"""
    q = query.strip()
    if not q:
        return []

    # 完全匹配（任意套）
    exact = _any_zh_to_en.get(q)
    if exact:
        return [exact]

    # 子串匹配，合并两套，去重
    seen_en: set[str] = set()
    results: list[tuple[int, str]] = []
    for zh_map in (_any_zh_to_en,):
        for zh, en in zh_map.items():
            if q in zh and en not in seen_en:
                seen_en.add(en)
                results.append((len(zh), en))
    results.sort()
    return [en for _, en in results[:limit]]


def has_chinese(s: str) -> bool:
    if not s:
        return False
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def register_community(en_name: str, zh_name: str):
    """运行时注册一条社区翻译（bazaardb 返回中文名时调用）"""
    if not en_name or not zh_name:
        return
    if not has_chinese(zh_name):
        return
    if en_name not in _comm_en_to_zh:
        _comm_en_to_zh[en_name] = zh_name
        _comm_zh_to_en[zh_name] = en_name
        _any_zh_to_en[zh_name] = en_name  # 社区先加，不覆盖官方


def reload():
    _load()


def stats() -> dict:
    return {
        "official": len(_official_en_to_zh),
        "community": len(_comm_en_to_zh),
        "total": len(_official_en_to_zh),
    }
_preload_community_from_cache()
