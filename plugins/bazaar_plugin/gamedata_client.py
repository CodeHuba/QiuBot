"""
GameData.db 客户端
从游戏本体 SQLite 数据库读取物品/技能数据，转换为 howbazaar 兼容格式
"""
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

# Action 类型 -> Attribute 键名映射（用于从 tier_attrs 取对应数值）
ACTION_ATTR_MAP = {
    "TActionPlayerDamage":          "DamageAmount",
    "TActionPlayerShieldApply":     "ShieldApplyAmount",
    "TActionPlayerHealApply":       "HealAmount",
    "TActionPlayerPoisonApply":     "PoisonApplyAmount",
    "TActionPlayerBurnApply":       "BurnApplyAmount",
    "TActionPlayerRegenApply":      "RegenApplyAmount",
    "TActionPlayerFreezeApply":     "FreezeAmount",
    "TActionPlayerSlowApply":       "SlowAmount",
    "TActionPlayerHasteApply":      "HasteAmount",
    "TActionPlayerGoldModify":      "Gold",
    "TActionPlayerChargeApply":     "ChargeAmount",
    # 附魔专用 action
    "TActionCardSlow":              "SlowAmount",
    "TActionCardFreeze":            "FreezeAmount",
    "TActionCardHaste":             "HasteAmount",
    "TActionCardCharge":            "ChargeAmount",
}

# SlowAmount/FreezeAmount/HasteAmount 单位是毫秒，需要转秒
MS_ATTRS = {"SlowAmount", "FreezeAmount", "HasteAmount", "ChargeAmount"}


def ms_to_s(ms: float) -> str:
    """毫秒转秒，整数时去掉小数点"""
    s = ms / 1000
    return str(int(s)) if s == int(s) else str(round(s, 1))


def fmt_val(v: Any, attr_key: str = "") -> str:
    """格式化数值，毫秒属性自动转秒"""
    if v is None:
        return "?"
    if attr_key in MS_ATTRS:
        try:
            return ms_to_s(float(v))
        except (ValueError, TypeError):
            pass
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else str(round(v, 1))
    return str(v)


def extract_value(action: dict, tier_attrs: dict) -> tuple[Any, str]:
    """
    从 action 中提取数值，返回 (值, attr_key)
    attr_key 用于判断是否需要毫秒转秒
    """
    atype = action.get("$type", "")

    # 修改属性类动作：读 AttributeType
    if atype in (
        "TActionCardModifyAttribute",
        "TAuraActionCardModifyAttribute",
        "TActionPlayerModifyAttribute",
        "TAuraActionPlayerModifyAttribute",
    ):
        attr_type = action.get("AttributeType", "")
        if attr_type and attr_type in tier_attrs:
            return tier_attrs[attr_type], attr_type
        val = action.get("Value", {})
        if not isinstance(val, dict):
            return None, ""
        vtype = val.get("$type", "")
        if vtype == "TFixedValue":
            return val.get("Value"), attr_type
        # TReferenceValueCardAttribute / TReferenceValuePlayerAttribute
        if "ReferenceValue" in vtype or vtype.endswith("Attribute"):
            ref_attr = val.get("AttributeType", "")
            if ref_attr and ref_attr in tier_attrs:
                return tier_attrs[ref_attr], ref_attr
        return None, ""

    # 直接动作：从 ACTION_ATTR_MAP 映射
    attr_key = ACTION_ATTR_MAP.get(atype, "")
    if attr_key and attr_key in tier_attrs:
        return tier_attrs[attr_key], attr_key

    # 尝试从 action 内嵌 Value 读固定值
    val = action.get("Value", {})
    if isinstance(val, dict) and val.get("$type") == "TFixedValue":
        return val.get("Value"), ""

    return None, ""


def build_tier_attrs(item_data: dict, tier_name: str) -> dict:
    """构建某个 tier 的完整属性（累加 Bronze→目标tier）"""
    tier_order = ["Bronze", "Silver", "Gold", "Diamond", "Legendary"]
    base: dict = {}
    for t in tier_order:
        tier = item_data.get("Tiers", {}).get(t, {})
        base.update(tier.get("Attributes", {}))
        if t == tier_name:
            break
    return base


def render_tooltip(
    text: str,
    abilities: dict,
    auras: dict,
    tier_attrs: dict,
) -> str:
    """渲染 tooltip 模板，替换 {ability.X} / {aura.X} 占位符"""

    def replace_ph(m: re.Match) -> str:
        ph = m.group(1)
        parts = ph.split(".")
        if len(parts) < 2:
            return m.group(0)

        prefix, ab_id = parts[0], parts[1]
        sub = parts[2] if len(parts) > 2 else ""

        if prefix == "ability":
            ab = abilities.get(ab_id)
            if ab is None:
                return m.group(0)
            if sub == "targets":
                action = ab.get("Action", {})
                tc = action.get("TargetCount")
                if isinstance(tc, dict) and tc.get("$type") == "TFixedValue":
                    return fmt_val(tc.get("Value"))
                return "1"
            v, ak = extract_value(ab.get("Action", {}), tier_attrs)
            return fmt_val(v, ak)

        elif prefix == "aura":
            aura = auras.get(ab_id)
            if aura is None:
                return m.group(0)
            if sub == "mod":
                action = aura.get("Action", {})
                val = action.get("Value", {})
                if isinstance(val, dict) and val.get("$type") == "TFixedValue":
                    return fmt_val(val.get("Value"))
            v, ak = extract_value(aura.get("Action", {}), tier_attrs)
            return fmt_val(v, ak)

        return m.group(0)

    return re.sub(r"\{([^}]+)\}", replace_ph, text)


def get_tier_tooltips(item_data: dict, tier_name: str) -> list[str]:
    """获取某个 tier 的 tooltip 列表（已渲染）"""
    tier_attrs = build_tier_attrs(item_data, tier_name)
    abilities = item_data.get("Abilities", {})
    auras = item_data.get("Auras", {})

    tooltips: list[str] = []

    # Cooldown
    cooldown = tier_attrs.get("CooldownMax")
    if cooldown:
        tooltips.append(f"Cooldown {ms_to_s(cooldown)}s")

    # Multicast
    multicast = tier_attrs.get("Multicast", 1)
    if multicast > 1:
        tooltips.append(f"Multicast {int(multicast)}")

    # 主 tooltips
    for t in item_data.get("Localization", {}).get("Tooltips", []):
        txt = t.get("Content", {}).get("Text", "")
        if txt:
            tooltips.append(render_tooltip(txt, abilities, auras, tier_attrs))

    return tooltips


def get_enchant_tooltips(item_data: dict, ench_name: str) -> list[str]:
    """获取附魔的 tooltip 列表"""
    ench = item_data.get("Enchantments", {}).get(ench_name, {})
    base_tier = item_data.get("StartingTier", "Bronze")
    base_attrs = build_tier_attrs(item_data, base_tier)
    ench_attrs = {**base_attrs, **ench.get("Attributes", {})}

    # 合并 base + 附魔的 abilities/auras
    all_abilities = {**item_data.get("Abilities", {}), **ench.get("Abilities", {})}
    all_auras = {**item_data.get("Auras", {}), **ench.get("Auras", {})}

    tooltips: list[str] = []
    for t in ench.get("Localization", {}).get("Tooltips", []):
        txt = t.get("Content", {}).get("Text", "")
        if txt:
            tooltips.append(render_tooltip(txt, all_abilities, all_auras, ench_attrs))
    return tooltips


def convert_item_to_howbazaar_format(item_data: dict) -> dict:
    """将 GameData.db 格式的 item 转换为 howbazaar 兼容格式"""
    loc = item_data.get("Localization", {})
    name = loc.get("Title", {}).get("Text", item_data.get("InternalName", "Unknown"))

    # 构建 tiers
    tiers: dict = {}
    for tier_name in ["Bronze", "Silver", "Gold", "Diamond", "Legendary"]:
        if tier_name in item_data.get("Tiers", {}):
            tiers[tier_name] = {"tooltips": get_tier_tooltips(item_data, tier_name)}

    # 构建 enchantments
    enchantments: list[dict] = []
    for ench_name in (item_data.get("Enchantments") or {}):
        tips = get_enchant_tooltips(item_data, ench_name)
        if tips:
            enchantments.append({"type": ench_name, "tooltips": tips})

    # unifiedTooltips：用 startingTier 的 tooltips
    unified = get_tier_tooltips(item_data, item_data.get("StartingTier", "Bronze"))

    return {
        "id": item_data.get("Id", ""),
        "name": name,
        "startingTier": item_data.get("StartingTier", "Bronze"),
        "tiers": tiers,
        "tags": item_data.get("Tags", []),
        "hiddenTags": item_data.get("HiddenTags", []),
        "customTags": [],
        "size": item_data.get("Size", "Medium"),
        "heroes": item_data.get("Heroes", []),
        "enchantments": enchantments,
        "quests": [],
        "unifiedTooltips": unified,
        "combatEncounters": [],
    }


def convert_skill_to_howbazaar_format(skill_data: dict) -> dict:
    """将 GameData.db 格式的 skill 转换为 howbazaar 兼容格式"""
    loc = skill_data.get("Localization", {})
    name = loc.get("Title", {}).get("Text", skill_data.get("InternalName", "Unknown"))

    tiers: dict = {}
    for tier_name in ["Bronze", "Silver", "Gold", "Diamond", "Legendary"]:
        if tier_name in skill_data.get("Tiers", {}):
            tiers[tier_name] = {"tooltips": get_tier_tooltips(skill_data, tier_name)}

    unified = get_tier_tooltips(skill_data, skill_data.get("StartingTier", "Bronze"))

    return {
        "id": skill_data.get("Id", ""),
        "name": name,
        "startingTier": skill_data.get("StartingTier", "Bronze"),
        "tiers": tiers,
        "tags": skill_data.get("Tags", []),
        "hiddenTags": skill_data.get("HiddenTags", []),
        "customTags": [],
        "heroes": skill_data.get("Heroes", []),
        "enchantments": [],
        "quests": [],
        "unifiedTooltips": unified,
        "combatEncounters": [],
    }


class GameDataClient:
    """从 GameData.db 读取并转换为 howbazaar 兼容格式"""

    def __init__(self, db_path: "str | Path"):
        self.db_path = Path(db_path)
        self._items: list[dict] = []
        self._skills: list[dict] = []

    def load(self) -> None:
        """加载并转换数据"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"GameData.db 不存在: {self.db_path}")

        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("SELECT Data FROM cards")
        rows = cur.fetchall()
        conn.close()

        items: list[dict] = []
        skills: list[dict] = []
        for (data,) in rows:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                d = json.loads(data)
            except Exception:
                continue

            card_type = d.get("$type")
            if card_type == "TCardItem":
                items.append(convert_item_to_howbazaar_format(d))
            elif card_type == "TCardSkill":
                skills.append(convert_skill_to_howbazaar_format(d))

        self._items = items
        self._skills = skills
        print(f"[GameDataClient] 已加载 {len(items)} 个物品, {len(skills)} 个技能")

    def items(self) -> list[dict]:
        return self._items

    def skills(self) -> list[dict]:
        return self._skills
