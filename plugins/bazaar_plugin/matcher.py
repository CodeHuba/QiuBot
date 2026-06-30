"""
模糊匹配 - 名字 → 实体
- 完全匹配 > 前缀 > 子串 > 词序匹配
- 大小写无关,去除标点和空白
- 支持中文搜索(经 translations 模块转英文后匹配)
"""
import re
from typing import Iterable

from . import translations


_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = _PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def find_matches(query: str, entities: Iterable[dict], name_field: str = "name", limit: int = 10) -> list[dict]:
    """返回最多 limit 条候选,按相关度排序。中文 query 自动用翻译表反查。"""
    if not query.strip():
        return []

    # 中文 query: 先用翻译表反查英文名,拿到的英文名再走标准匹配
    if translations.has_chinese(query):
        en_names = translations.search_zh(query, limit=limit)
        if not en_names:
            return []
        # 按 en_names 顺序构造结果
        name_set = {n.lower() for n in en_names}
        out = []
        for ent in entities:
            nm = (ent.get(name_field) or "").lower()
            if nm in name_set:
                out.append(ent)
        # 保持 en_names 的顺序
        order = {n.lower(): i for i, n in enumerate(en_names)}
        out.sort(key=lambda e: order.get((e.get(name_field) or "").lower(), 9999))
        return out[:limit]

    q = _norm(query)
    q_tokens = q.split()

    exact: list[dict] = []
    prefix: list[dict] = []
    substr: list[dict] = []
    tokens: list[dict] = []

    for ent in entities:
        nm = ent.get(name_field) or ""
        n = _norm(nm)
        if not n:
            continue
        if n == q:
            exact.append(ent)
        elif n.startswith(q):
            prefix.append(ent)
        elif q in n:
            substr.append(ent)
        else:
            # 词序无关:所有 query token 都出现在 name 里
            if q_tokens and all(t in n for t in q_tokens):
                tokens.append(ent)

    seen: set[str] = set()
    out: list[dict] = []
    for bucket in (exact, prefix, substr, tokens):
        for ent in bucket:
            key = ent.get("id") or ent.get(name_field)
            if key in seen:
                continue
            seen.add(key)
            out.append(ent)
            if len(out) >= limit:
                return out
    return out


def find_one(query: str, entities: Iterable[dict], name_field: str = "name") -> tuple[dict | None, list[dict]]:
    """命中 1 条 → (ent, []); 多条 → (None, candidates)"""
    matches = find_matches(query, entities, name_field=name_field, limit=10)
    if not matches:
        return None, []
    # 中文 query 命中第一条直接返回(translations.search_zh 已经返回了排好序的英文名)
    if translations.has_chinese(query):
        if len(matches) == 1:
            return matches[0], []
        # 多条:检查第一条是否完全匹配中文 query
        first_en = matches[0].get(name_field) or ""
        zh = translations.get_zh(first_en)
        if zh and zh == query.strip():
            return matches[0], []
        return None, matches
    # 完全匹配(去标点后)直接选第一条
    q = _norm(query)
    if _norm(matches[0].get(name_field) or "") == q:
        return matches[0], []
    if len(matches) == 1:
        return matches[0], []
    return None, matches
