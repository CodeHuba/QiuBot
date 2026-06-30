"""
Tooltip 翻译缓存 + Claude API 实时翻译
- 首次查询 → 调 Claude 翻译 → 存缓存
- 二次查询 → 直接读缓存
- 缓存版本号跟 howbazaar 的 items/skills version 同步
"""
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# 加载 .env(要在读环境变量之前)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

CACHE_FILE = Path(__file__).parent / "cache" / "tooltip_translations.json"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

# 术语表（官方 GameData.db 提取，保证翻译一致性）
GLOSSARY = {
    "Ammo": "弹药",
    "Apparel": "服饰",
    "Aquatic": "水生",
    "Bronze": "青铜",
    "Burn": "燃烧",
    "Burned": "灼烧",
    "Burns": "灼烧",
    "Charge": "充能",
    "Charges": "充能",
    "Chilled": "冰冻",
    "Clock": "时钟",
    "Cooldown": "冷却",
    "Cooldowns": "冷却",
    "Core": "核心",
    "Crit": "暴击",
    "CritText": "暴击",
    "Crits": "暴击",
    "Damage": "伤害",
    "Damages": "伤害",
    "Destroy": "摧毁",
    "Destroys": "摧毁",
    "Diamond": "钻石",
    "Dinosaur": "恐龙",
    "Dinosaurs": "恐龙",
    "Dragon": "龙",
    "Drone": "无人机",
    "Drones": "无人机",
    "Dualcast": "双重施放",
    "Enchant": "附魔",
    "Enchants": "附魔",
    "Enraged": "狂怒",
    "Exit": "离开",
    "Experience": "经验",
    "Flying": "飞行",
    "Food": "食物",
    "Freeze": "冻结",
    "Freezes": "冰冻",
    "Friend": "好友",
    "Friends": "好友",
    "Frozen": "冰冻",
    "Gold": "黄金",
    "Haste": "加速",
    "Hastes": "加速",
    "Heal": "治疗",
    "Healing": "治疗",
    "Heals": "治疗",
    "Health": "生命值",
    "Heated": "灼热",
    "Income": "收益",
    "Ingredient": "材料",
    "Ingredients": "材料",
    "Item": "物品",
    "Joy": "欢愉",
    "Key": "钥匙",
    "Keys": "钥匙",
    "Lifesteal": "吸血",
    "Loot": "战利品",
    "Map": "地图",
    "Maps": "地图",
    "Merchant": "商人",
    "Multicast": "多重施放",
    "NestedCardEffect": "卡牌效果",
    "NestedTooltipBase": "基础",
    "Non-": "非",
    "Poison": "毒素",
    "Poisoned": "中毒",
    "Poisons": "中毒",
    "Potion": "药水",
    "Potions": "药水",
    "Prestige": "声望",
    "Properties": "地产",
    "Property": "地产",
    "Quadcast": "四重施放",
    "Rage": "怒气",
    "Ray": "射线",
    "Rays": "射线",
    "Reagent": "试剂",
    "Reagents": "试剂",
    "Regeneration": "回复",
    "Regen": "回复",
    "Regens": "回复",
    "Relic": "遗物",
    "Relics": "遗物",
    "Reload": "装填",
    "Reloads": "装填",
    "Repair": "修复",
    "Reroll": "刷新",
    "Shield": "护盾",
    "Shielding": "护盾",
    "Shields": "护盾",
    "Silver": "白银",
    "Skill": "技能",
    "Slow": "减速",
    "Slows": "减速",
    "Stash": "仓库",
    "Tech": "科技",
    "Tool": "工具",
    "Tools": "工具",
    "Toy": "玩具",
    "Toys": "玩具",
    "Transform": "变形",
    "Transforms": "变形",
    "Trap": "陷阱",
    "Tricast": "三重施放",
    "Unsellable": "无法出售",
    "Upgrade": "升级",
    "Upgrades": "升级",
    "Value": "价值",
    "Vehicle": "载具",
    "Vehicles": "载具",
    "Victories": "胜场",
    "VictoriesRanked": "排位胜场",
    "Weapon": "武器",
    "Weapons": "武器",
}

_cache: dict = {}
_version: str = ""


def _load():
    global _cache, _version
    if not CACHE_FILE.exists():
        _cache = {}
        _version = ""
        return
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        _version = data.get("version", "")
        _cache = data.get("cache", {})
        print(f"[tooltip_trans] 已加载 {len(_cache)} 条翻译缓存 (version={_version})")
    except Exception as e:
        print(f"[tooltip_trans] 加载失败: {e}")
        _cache = {}
        _version = ""


def _save():
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": _version, "cache": _cache}
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


_load()


def set_version(ver: str):
    """更新缓存版本号(从 howbazaar 数据同步)。"""
    global _version
    if _version != ver:
        print(f"[tooltip_trans] 版本更新: {_version} → {ver}, 清空旧缓存")
        _cache.clear()
        _version = ver
        _save()


def get_translation(text_en: str, card_name: str = "", tier: str = "") -> str | None:
    """查缓存,返回中文 tooltip。无缓存返回 None。"""
    if not text_en.strip():
        return None
    # cache key: card_name|tier|text (text 保证唯一性)
    key = f"{card_name}|{tier}|{text_en}"
    return _cache.get(key)


async def translate_tooltip(text_en: str, card_name: str = "", tier: str = "") -> str:
    """
    调 Claude API 翻译,翻译后存入缓存。
    返回中文 tooltip。失败则返回原英文。
    """
    if not text_en.strip():
        return text_en

    # 1. 检查缓存
    cached = get_translation(text_en, card_name, tier)
    if cached:
        return cached

    # 2. 无缓存 → 调 Claude
    if not ANTHROPIC_API_KEY:
        print(f"[tooltip_trans] ANTHROPIC_API_KEY 未配置,跳过翻译")
        return text_en

    # 构造 prompt
    glossary_lines = "\n".join(f"- {en}: {zh}" for en, zh in GLOSSARY.items())
    prompt = f"""你是 The Bazaar 游戏的专业翻译。
请将以下效果文本翻译成简体中文,遵循术语表:

{glossary_lines}

原文:
{text_en}

要求:
1. 只返回翻译结果,不要解释、不要加引号
2. 保持数字、符号原样(+4、%等)
3. 术语必须严格按照术语表
4. 语句通顺自然

翻译:"""

    try:
        async with httpx.AsyncClient(timeout=30) as cli:
            r = await cli.post(
                f"{ANTHROPIC_BASE_URL}/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ANTHROPIC_MODEL,
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            body = r.json()
            content = body.get("content", [])
            if content and content[0].get("type") == "text":
                zh = content[0].get("text", "").strip()
                # 3. 存缓存
                key = f"{card_name}|{tier}|{text_en}"
                _cache[key] = zh
                _save()
                print(f"[tooltip_trans] 已翻译并缓存: {card_name}|{tier}")
                return zh
    except Exception as e:
        print(f"[tooltip_trans] 翻译失败: {e}")

    # 失败 → 返回原文
    return text_en


def stats() -> dict:
    return {"cached": len(_cache), "version": _version}
