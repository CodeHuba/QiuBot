"""统一 Bazaar 卡牌数据文件路径。"""
from __future__ import annotations

import os
from pathlib import Path


def get_gamedata_db_path(
    fallback: str | Path | None = None,
    *,
    require_exists: bool = False,
) -> Path | None:
    """返回 GameData.db 路径。

    优先使用 GAMEDATA_DB；未配置时使用调用方提供的插件缓存路径。
    require_exists=True 时，候选不存在则返回 None。
    """
    configured = os.getenv("GAMEDATA_DB", "").strip()
    candidate = Path(configured).expanduser() if configured else (
        Path(fallback).expanduser() if fallback is not None else None
    )
    if candidate is None:
        return None
    if require_exists and not candidate.is_file():
        return None
    return candidate
