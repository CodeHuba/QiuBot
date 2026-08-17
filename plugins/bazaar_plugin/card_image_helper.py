"""
card_images.json 读取辅助函数
"""
import json
from pathlib import Path
from typing import Optional

_CACHE_FILE = Path(__file__).resolve().parent / 'cache' / 'card_images.json'
_CACHE = None


def _load():
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(_CACHE_FILE.read_text(encoding='utf-8'))
        except Exception:
            _CACHE = {'cards': {}}
    return _CACHE


def get_card_image(card_id: str = None, internal_name: str = None) -> Optional[dict]:
    """
    根据 card_id 或 internal_name 获取图片信息
    返回 {'art': '...', 'artLarge': '...', 'artBlur': '...', 'name': '...'}
    """
    cards = _load().get('cards', {})

    if card_id and card_id in cards:
        return cards[card_id]

    if internal_name:
        for info in cards.values():
            if info.get('internalName') == internal_name:
                return info

    return None


def get_art_url(card_id: str = None, internal_name: str = None, size: str = 'art') -> Optional[str]:
    """
    获取图片 URL
    size: 'art'(256px) | 'artLarge'(400px) | 'artBlur'(base64占位)
    """
    info = get_card_image(card_id, internal_name)
    return info.get(size, '') if info else None
