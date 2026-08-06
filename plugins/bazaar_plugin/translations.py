"""
英文 → 中文翻译表
- 社区翻译 (translations_community.json): 英文名 → 社区中文名 (来自 bazaardb.gg)
- 运行时从 bazaardb 磁盘缓存预热，查询时自动注册
"""
import json
from pathlib import Path

CACHE_DIR        = Path(__file__).parent / "cache"
TRANS_COMM_FILE  = CACHE_DIR / "translations_community.json"
TRANS_OFFIC_FILE = CACHE_DIR / "translations.json"  # 官方翻译（英文名 -> 中文名）

_comm_en_to_zh: dict[str, str] = {}
_comm_zh_to_en: dict[str, str] = {}
_hash_to_zh: dict[str, str] = {}  # hash -> 中文（从 zh-CN.bytes 加载）


def _load():
    global _comm_en_to_zh, _comm_zh_to_en, _hash_to_zh
    # 1. 先加载官方翻译作为底层（社区翻译优先级更高，后面会覆盖）
    if TRANS_OFFIC_FILE.exists():
        try:
            data = json.loads(TRANS_OFFIC_FILE.read_text(encoding="utf-8"))
            _comm_en_to_zh.update(data)
            _comm_zh_to_en.update({zh: en for en, zh in data.items()})
            print(f"[translations] 官方翻译: {len(data)} 条")
        except Exception as e:
            print(f"[translations] 官方翻译加载失败: {e}")
    # 2. 社区翻译覆盖（优先级更高）
    if TRANS_COMM_FILE.exists():
        try:
            data = json.loads(TRANS_COMM_FILE.read_text(encoding="utf-8"))
            _comm_en_to_zh.update(data)
            _comm_zh_to_en.update({zh: en for en, zh in data.items()})
            print(f"[translations] 社区翻译: {len(data)} 条")
        except Exception as e:
            print(f"[translations] 社区翻译加载失败: {e}")
    # 3. 加载 hash -> 中文映射（用于 tooltip Key 查翻译）
    zh_bytes_file = CACHE_DIR.parent.parent / "AppData/LocalLow/Tempo Storm/The Bazaar/prod/cache/translations/zh-CN.bytes"
    if not zh_bytes_file.exists():
        # Windows 游戏目录不在 WSL，用云服务器备份的 JSON
        zh_json_file = CACHE_DIR / "zh-CN.json"
        if zh_json_file.exists():
            try:
                import json as _j
                data = _j.loads(zh_json_file.read_text(encoding="utf-8"))
                _hash_to_zh.update(data)
                print(f"[translations] hash映射: {len(data)} 条 (从 JSON)")
            except Exception as e:
                print(f"[translations] hash映射加载失败: {e}")
    else:
        try:
            import sqlite3
            conn = sqlite3.connect(str(zh_bytes_file))
            for row in conn.execute("SELECT hash, text FROM translation").fetchall():
                _hash_to_zh[row[0]] = row[1]
            conn.close()
            print(f"[translations] hash映射: {len(_hash_to_zh)} 条 (从 zh-CN.bytes)")
        except Exception as e:
            print(f"[translations] hash映射加载失败: {e}")


_load()


def _preload_community_from_cache():
    """启动时从 bazaardb 磁盘缓存批量注册社区翻译"""
    import json as _json
    count = 0
    try:
        for f in CACHE_DIR.glob("bazaardb_card_*.json"):
            try:
                card = _json.loads(f.read_text(encoding="utf-8"))
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
    """英文名 → 社区中文名"""
    if not name_en:
        return None
    return _comm_en_to_zh.get(name_en) or _comm_en_to_zh.get(name_en.lower())


def get_zh_both(name_en: str) -> tuple[str | None, str | None]:
    """兼容旧接口，返回 (None, 社区中文)"""
    return None, get_zh(name_en)


def get_en(name_zh: str) -> str | None:
    """中文名 → 英文名"""
    if not name_zh:
        return None
    return _comm_zh_to_en.get(name_zh.strip())


def search_zh(query: str, limit: int = 10) -> list[str]:
    """中文模糊查询，返回英文名列表"""
    q = query.strip()
    if not q:
        return []
    exact = _comm_zh_to_en.get(q)
    if exact:
        return [exact]
    results = []
    for zh, en in _comm_zh_to_en.items():
        if q in zh:
            results.append((len(zh), en))
    results.sort()
    return [en for _, en in results[:limit]]


def has_chinese(s: str) -> bool:
    if not s:
        return False
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def register_community(en_name: str, zh_name: str):
    """运行时注册一条社区翻译"""
    if not en_name or not zh_name or not has_chinese(zh_name):
        return
    _comm_en_to_zh[en_name] = zh_name
    _comm_zh_to_en[zh_name] = en_name


def reload():
    _load()


def stats() -> dict:
    return {"community": len(_comm_en_to_zh), "total": len(_comm_en_to_zh)}


_preload_community_from_cache()


def get_zh_by_key(key: str) -> str | None:
    """通过 hash key 查中文翻译（用于 tooltip 的 Key 字段）"""
    if not key:
        return None
    return _hash_to_zh.get(key)
