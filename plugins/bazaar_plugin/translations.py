"""
英文 → 中文翻译表(从 bazaardb.gg 抓取)
- en_to_zh: 英文名 → 中文名
- zh_to_en: 中文名 → 英文名(反查,用于中文搜索)
- 大小写不敏感的英文索引
"""
import json
from pathlib import Path

TRANS_FILE = Path(__file__).parent / "cache" / "translations.json"

_en_to_zh: dict[str, str] = {}
_zh_to_en: dict[str, str] = {}
_en_lower_to_zh: dict[str, str] = {}


def _load():
    global _en_to_zh, _zh_to_en, _en_lower_to_zh
    if not TRANS_FILE.exists():
        print(f"[translations] 翻译文件不存在: {TRANS_FILE}")
        return
    try:
        data = json.loads(TRANS_FILE.read_text(encoding="utf-8"))
        _en_to_zh = data
        _zh_to_en = {zh: en for en, zh in data.items()}
        _en_lower_to_zh = {en.lower(): zh for en, zh in data.items()}
        print(f"[translations] 已加载 {len(_en_to_zh)} 条翻译")
    except Exception as e:
        print(f"[translations] 加载失败: {e}")


_load()


def get_zh(name_en: str) -> str | None:
    """英文名 → 中文名,大小写不敏感。"""
    if not name_en:
        return None
    return _en_to_zh.get(name_en) or _en_lower_to_zh.get(name_en.lower())


def get_en(name_zh: str) -> str | None:
    """中文名 → 英文名,完全匹配。"""
    if not name_zh:
        return None
    return _zh_to_en.get(name_zh.strip())


def search_zh(query: str, limit: int = 10) -> list[str]:
    """中文模糊查询,返回英文名列表(子串匹配)。"""
    q = query.strip()
    if not q:
        return []
    # 完全匹配
    exact = _zh_to_en.get(q)
    if exact:
        return [exact]
    # 子串匹配
    results = []
    for zh, en in _zh_to_en.items():
        if q in zh:
            results.append(en)
            if len(results) >= limit:
                break
    return results


def has_chinese(s: str) -> bool:
    """检查字符串是否包含中文字符。"""
    if not s:
        return False
    return any('\u4e00' <= c <= '\u9fff' for c in s)


def reload():
    """重新加载翻译文件。"""
    _load()


def stats() -> dict:
    return {"total": len(_en_to_zh)}
