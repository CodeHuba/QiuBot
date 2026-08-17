"""
GameData.db 客户端
从游戏本体 SQLite 数据库读取物品/技能数据，转换为 howbazaar 兼容格式
"""
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

# Action 类型 -> Amount Attribute 键名映射（逆向自 BazaarGameClient TooltipComponentAbility.GetAmountAttribute）
ACTION_ATTR_MAP = {
    "TActionPlayerDamage":          "DamageAmount",
    "TActionPlayerShieldApply":     "ShieldApplyAmount",
    "TActionPlayerHeal":             "HealAmount",
    "TActionPlayerHealApply":       "HealAmount",
    "TActionPlayerPoisonApply":     "PoisonApplyAmount",
    "TActionPlayerPoisonRemove":    "PoisonRemoveAmount",
    "TActionPlayerBurnApply":       "BurnApplyAmount",
    "TActionPlayerBurnRemove":      "BurnRemoveAmount",
    "TActionPlayerRegenApply":      "RegenApplyAmount",
    "TActionPlayerRegenRemove":     "RegenRemoveAmount",
    "TActionPlayerRageApply":       "RageApplyAmount",
    "TActionPlayerRageRemove":      "RageRemoveAmount",
    "TActionPlayerShieldRemove":    "ShieldRemoveAmount",
    "TActionPlayerTempoApply":      "TempoApplyAmount",
    "TActionPlayerTempoRemove":     "TempoRemoveAmount",
    "TActionPlayerGoldModify":      "Gold",
    # 卡牌动作
    "TActionCardSlow":              "SlowAmount",
    "TActionCardFreeze":            "FreezeAmount",
    "TActionCardHaste":             "HasteAmount",
    "TActionCardCharge":            "ChargeAmount",
    "TActionCardReload":            "ReloadAmount",
    # 旧版兼容
    "TActionPlayerFreezeApply":     "FreezeAmount",
    "TActionPlayerSlowApply":       "SlowAmount",
    "TActionPlayerHasteApply":      "HasteAmount",
    "TActionPlayerChargeApply":     "ChargeAmount",
}

# Action 类型 -> Targets Attribute 键名映射（逆向自 BazaarGameClient TooltipComponentAbility.GetTargetsAttribute）
ACTION_TARGETS_MAP = {
    "TActionCardCharge":            "ChargeTargets",
    "TActionCardDestroy":           "DestroyTargets",
    "TActionCardDisable":           "DisableTargets",
    "TActionCardEnchantRemove":     "EnchantRemoveTargets",
    "TActionCardForceUse":          "ForceUseTargets",
    "TActionCardFreeze":            "FreezeTargets",
    "TActionCardHaste":             "HasteTargets",
    "TActionCardReload":            "ReloadTargets",
    "TActionCardRepair":            "RepairTargets",
    "TActionCardSlow":              "SlowTargets",
    "TActionCardTransform":         "TransformTargets",
    "TActionCardTransformDestroyed":"TransformTargets",
    "TActionCardUpgrade":           "UpgradeTargets",
    "TActionCardFlyingStart":       "FlyingTargets",
    "TActionCardFlyingStop":        "FlyingTargets",
    "TActionCardFlyingToggle":      "FlyingTargets",
}

# 这些属性单位是毫秒，需要转秒显示
MS_ATTRS = {"SlowAmount", "FreezeAmount", "HasteAmount", "ChargeAmount", "ReloadAmount", "FlatCooldownReduction", "PercentCooldownReduction",
            "CooldownMax"}


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
        val = action.get("Value", {})
        if not isinstance(val, dict):
            # 直接从 tier_attrs 取
            if attr_type and attr_type in tier_attrs:
                return tier_attrs[attr_type], attr_type
            return None, ""
        vtype = val.get("$type", "")
        if vtype == "TFixedValue":
            return val.get("Value"), attr_type
        # TReferenceValueCardAttribute / TReferenceValuePlayerAttribute（可能带 Modifier）
        if "ReferenceValue" in vtype or vtype.endswith("Attribute"):
            ref_attr = val.get("AttributeType", "")
            ref_val = tier_attrs.get(ref_attr) if ref_attr else None
            if ref_val is not None:
                # 处理 Modifier（如 Multiply * 5.0）
                modifier = val.get("Modifier")
                if isinstance(modifier, dict):
                    mod_mode = modifier.get("ModifyMode", "")
                    mod_val_obj = modifier.get("Value", {})
                    mod_val = mod_val_obj.get("Value") if isinstance(mod_val_obj, dict) else None
                    if mod_val is not None:
                        if mod_mode == "Multiply":
                            ref_val = ref_val * mod_val
                        elif mod_mode == "Add":
                            ref_val = ref_val + mod_val
                return ref_val, ref_attr
        # 最后 fallback：从 tier_attrs 取 AttributeType
        if attr_type and attr_type in tier_attrs:
            return tier_attrs[attr_type], attr_type
        return None, ""

    # 直接动作：从 ACTION_ATTR_MAP 映射
    attr_key = ACTION_ATTR_MAP.get(atype, "")
    if attr_key and attr_key in tier_attrs:
        return tier_attrs[attr_key], attr_key

    # 尝试从 action 内嵌 Value 读固定值
    val = action.get("Value", {})
    if isinstance(val, dict) and val.get("$type") == "TFixedValue":
        return val.get("Value"), ""

    # TActionGameSpawnCards / TActionGameDealCards: 读 SpawnContext.Limit
    if atype in ("TActionGameSpawnCards", "TActionGameDealCards"):
        spawn_ctx = action.get("SpawnContext", {})
        limit = spawn_ctx.get("Limit", {})
        if isinstance(limit, dict) and limit.get("$type") == "TFixedValue":
            return limit.get("Value"), ""

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


def annotate_implicit_ability_attributes(text: str, abilities: dict) -> str:
    """为省略属性名的 {ability.X} 补全伤害/治疗/护盾等单位。

    仅当该占位符之后、下一占位符之前的模板片段没有写出对应属性时追加，
    因此不会把“造成{ability.X}伤害”渲染为“伤害伤害”。
    """
    attr_zh = {
        "DamageAmount": "伤害",
        "HealAmount": "治疗",
        "ShieldApplyAmount": "护盾",
        "ShieldAmount": "护盾",
        "PoisonApplyAmount": "剧毒",
        "BurnApplyAmount": "灼烧",
        "RegenApplyAmount": "生命再生",
    }
    matches = list(re.finditer(r"\{ability\.([^}.]+)\}", text))
    if not matches:
        return text
    parts, pos = [], 0
    effect_words = tuple(set(attr_zh.values()))
    for index, match in enumerate(matches):
        parts.append(text[pos:match.end()])
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        following = text[match.end():next_start]
        action = (abilities.get(match.group(1)) or {}).get("Action") or {}
        label = attr_zh.get(action.get("AttributeType", ""))
        if label and not any(word in following for word in effect_words):
            parts.append(label)
        pos = match.end()
    parts.append(text[pos:])
    return "".join(parts)


def render_tooltip(
    text: str,
    abilities: dict,
    auras: dict,
    tier_attrs: dict,
) -> str:
    """渲染 tooltip 模板，替换 {ability.X} / {aura.X} 占位符。
    逻辑对齐 BazaarGameClient TooltipComponentAbility，支持 {A ?? B} coalesce。
    """

    def resolve_single(ph: str):
        parts = ph.strip().split(".")
        if len(parts) < 2:
            return None
        prefix, ab_id = parts[0], parts[1]
        sub = parts[2] if len(parts) > 2 else ""

        if prefix == "ability":
            ab = abilities.get(ab_id)
            if ab is None:
                return None
            action = ab.get("Action", {})
            atype = action.get("$type", "")
            if sub == "targets":
                targets_attr = ACTION_TARGETS_MAP.get(atype)
                if targets_attr and targets_attr in tier_attrs:
                    return fmt_val(tier_attrs[targets_attr])
                tc = action.get("TargetCount")
                if isinstance(tc, dict) and tc.get("$type") == "TFixedValue":
                    return fmt_val(tc.get("Value"))
                return "1"
            if sub == "mod":
                # {ability.X.mod} 取 Action.Value.Modifier.Value（通常是 TReferenceValueCardAttribute）
                # 即倍率因子，从 tier_attrs 中解析
                val = action.get("Value", {})
                if isinstance(val, dict):
                    modifier = val.get("Modifier")
                    if isinstance(modifier, dict):
                        mod_val_obj = modifier.get("Value", {})
                        if isinstance(mod_val_obj, dict):
                            mvtype = mod_val_obj.get("$type", "")
                            if mvtype == "TFixedValue":
                                return fmt_val(mod_val_obj.get("Value"))
                            if "ReferenceValue" in mvtype or mvtype.endswith("Attribute"):
                                ref_attr = mod_val_obj.get("AttributeType", "")
                                if ref_attr and ref_attr in tier_attrs:
                                    return fmt_val(tier_attrs[ref_attr], ref_attr)
                return None
            v, ak = extract_value(action, tier_attrs)
            if v is None:
                return "?"
            return fmt_val(v, ak)

        elif prefix == "aura":
            aura = auras.get(ab_id)
            if aura is None:
                return None
            action = aura.get("Action", {})
            if sub == "mod":
                val = action.get("Value", {})
                if isinstance(val, dict) and val.get("$type") == "TFixedValue":
                    return fmt_val(val.get("Value"))
            v, ak = extract_value(action, tier_attrs)
            if v is None:
                return None
            return fmt_val(v, ak)

        return None

    def replace_ph(m: re.Match) -> str:
        ph = m.group(1)
        if "??" in ph:
            left, right = ph.split("??", 1)
            r = resolve_single(left.strip())
            if r is not None:
                return r
            r = resolve_single(right.strip())
            return r if r is not None else m.group(0)
        r = resolve_single(ph)
        return r if r is not None else m.group(0)

    return re.sub(r"\{([^}]+)\}", replace_ph, text)



def _resolve_encounter_name(card_id: str, db_path: str = "") -> str:
    """根据遭遇卡 UUID 查对应英雄名（用于 Quest 条件显示）"""
    if not db_path or not card_id:
        return "?"
    try:
        from . import translations as trans
        conn = __import__("sqlite3").connect(str(db_path))
        rows = conn.execute("SELECT Data FROM cards").fetchall()
        conn.close()
        card_data_module = __import__("json")
        for r in rows:
            raw = r[0]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            d = card_data_module.loads(raw)
            if d.get("Id") == card_id:
                loc_text = (d.get("Localization") or {}).get("Title", {}).get("Text", "")
                loc_key  = (d.get("Localization") or {}).get("Title", {}).get("Key", "")
                zh = trans.get_zh(loc_text) or trans.get_zh_by_key(loc_key) or loc_text
                return zh or "?"
    except Exception:
        pass
    return "?"

def get_quest_tooltips(item_data: dict, tier_name: str, db_path: str = "") -> list[dict]:
    """解析 Quest 条件和奖励，返回列表 [{condition, reward_tooltips}]"""
    TRIGGER_ZH = {
        "TTriggerOnCardFired":            "触发本卡",
        "TTriggerOnCardUsed":             "使用本卡",
        "TTriggerOnCardSold":             "出售本卡",
        "TTriggerOnCardBought":           "购买本卡",
        "TTriggerOnEncounterSelected":    "选择一个遭遇",
        "TTriggerOnDayStart":             "每天开始",
        "TTriggerOnCombatStart":          "战斗开始",
        "TTriggerOnCombatEnd":            "战斗结束",
        "TTriggerOnPlayerDamaged":        "受到伤害",
        "TTriggerOnPlayerKilled":         "击杀对手",
        "TTriggerOnCardPurchased":        "购买物品",
        "TTriggerOnCardAttributeChanged": "属性提升时",
        "TTriggerOnItemUsed":             "使用物品时",
        "TTriggerOnPlayerHealthChanged":  "生命值变化时",
        "TTriggerOnTurnStart":            "回合开始",
        "TTriggerOnTurnEnd":              "回合结束",
    }
    ATTR_ZH = {
        "Quest_1": "任务1", "Quest_2": "任务2", "Quest_3": "任务3",
        "Quest_4": "任务4", "Quest_5": "任务5",
    }
    TIER_ZH = {"Bronze": "铜", "Silver": "银", "Gold": "金", "Diamond": "钻", "Legendary": "传说"}
    COND_TYPE_ZH = {
        "TCardConditionalTier": lambda c: "品质为" + "/".join(TIER_ZH.get(t, t) for t in (c.get("Tiers") or [])),
        "TCardConditionalTag":  lambda c: "有标签" + str(c.get("Tag", "")),
        "TCardConditionalId":   lambda c: _resolve_encounter_name(c.get("Id", ""), db_path),
    }

    quests = item_data.get("Quests") or []
    tier_attrs = build_tier_attrs(item_data, tier_name)
    abilities = item_data.get("Abilities", {})
    auras = item_data.get("Auras", {})
    result = []

    for qg in quests:
        for entry in (qg.get("Entries") or []):
            # 触发条件
            trigger = entry.get("Trigger") or {}
            ttype = trigger.get("$type", "")
            tname = TRIGGER_ZH.get(ttype, ttype.replace("TTriggerOn", ""))
            cond = trigger.get("Conditions")
            cond_str = ""
            if cond:
                ctype = cond.get("$type", "")
                handler = COND_TYPE_ZH.get(ctype)
                if handler:
                    try:
                        resolved = handler(cond)
                        # TCardConditionalId 表示"选择特定英雄的遭遇"，嵌入 trigger 描述
                        if ctype == "TCardConditionalId" and ttype == "TTriggerOnEncounterSelected":
                            tname = f"选择[{resolved}]的遭遇"
                        else:
                            cond_str = "（" + resolved + "）"
                    except Exception:
                        pass
            target = entry.get("Target", 1)
            condition_text = f"{tname}{cond_str} x{target}" if target > 1 else f"{tname}{cond_str}"

            # 奖励
            reward = entry.get("Reward") or {}
            reward_tips = []
            # 奖励 tooltip 文本
            rew_loc = reward.get("Localization") or {}
            for t in rew_loc.get("Tooltips") or []:
                txt = (t.get("Content") or {}).get("Text", "")
                if txt:
                    # 奖励有自己的 abilities/auras，合并后渲染
                    rew_abs = {**abilities, **(reward.get("Abilities") or {})}
                    rew_auras = {**auras, **(reward.get("Auras") or {})}
                    # 奖励属性：优先用 tier-specific，fallback 到通用
                    rew_tiers = reward.get("Tiers") or {}
                    rew_attrs = {**tier_attrs}
                    if tier_name in rew_tiers:
                        rew_attrs.update(rew_tiers[tier_name].get("Attributes") or {})
                    elif reward.get("Attributes"):
                        rew_attrs.update(reward["Attributes"])
                    from . import translations as _trans
                    zh_tpl = _trans.get_tooltip_zh(txt) or (_trans.get_zh_by_key(t.get("Content", {}).get("Key", "")) if t.get("Content", {}).get("Key") else None) or txt
                    reward_tips.append(render_tooltip(zh_tpl, rew_abs, rew_auras, rew_attrs))

            result.append({
                "condition": condition_text,
                "reward_tooltips": reward_tips,
            })

    return result


def get_tier_tooltips(item_data: dict, tier_name: str) -> list[str]:
    """获取某个 tier 的 tooltip 列表（已渲染，含 CD）"""
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
    if multicast and multicast > 1:
        tooltips.append(f"Multicast {int(multicast)}")

    # 主 tooltips（按 TooltipCondition 过滤，不展示隐藏条件的）
    for t in item_data.get("Localization", {}).get("Tooltips", []):
        tip_cond = t.get("TooltipCondition")
        if tip_cond and tip_cond not in (None, "None"):
            continue  # Chilled/Heated/Enraged 等状态条件 tooltip 跳过
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

    from . import translations as trans
    tooltips: list[str] = []
    for t in ench.get("Localization", {}).get("Tooltips", []):
        txt = t.get("Content", {}).get("Text", "")
        if txt:
            # 先取中文模板（保留占位符），再渲染数值
            zh_tpl = trans.get_tooltip_zh(txt) or txt
            tooltips.append(render_tooltip(zh_tpl, all_abilities, all_auras, ench_attrs))
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
        "quests": get_quest_tooltips(item_data, item_data.get("StartingTier", "Bronze")),
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


TIER_ZH   = {"Bronze": "铜", "Silver": "银", "Gold": "金", "Diamond": "钻", "Legendary": "传说"}
HERO_ZH   = {
    "Common": "通用", "Pygmalien": "皮格马利翁", "Vanessa": "瓦内萨",
    "Dooley": "杜利", "Stelle": "斯特尔", "Jules": "朱尔斯",
    "Mak": "马克", "The Dragons": "双龙",
    "Hero8": "双龙",
}
TAG_ZH    = {
    "Weapon": "武器", "Tool": "工具", "Food": "食物", "Property": "房产",
    "Friend": "同伴", "Vehicle": "载具", "Damage": "伤害", "Shield": "护盾",
    "Heal": "治疗", "Poison": "毒", "Burn": "灼烧", "Slow": "减速",
    "Freeze": "冻结", "Haste": "加速", "Loot": "战利品", "Instrument": "乐器", "Dragon": "龙", "Aquatic": "水生", "Core": "核心", "Dinosaur": "恐龙", "Drone": "无人机", "Merchant": "商人", "Potion": "药水", "Ray": "射线", "Reagent": "试剂", "Relic": "遗物", "Tech": "科技", "Toy": "玩具", "Trap": "陷阱", "Apparel": "服装",
}
ENC_ZH    = {
    "Golden": "黄金", "Heavy": "沉重", "Icy": "寒冰", "Turbo": "疾速",
    "Shielded": "护盾", "Restorative": "回复", "Toxic": "毒素",
    "Fiery": "炽焰", "Shiny": "闪亮", "Obsidian": "黑曜石",
    "Deadly": "致命", "Radiant": "辉耀", "Mossy": "长青",
}


def format_card_from_raw(raw: dict, zh_name: str = "", db_path: str = "") -> str:
    """将 GameData.db 原始 dict 格式化为可读文本（用于 #bz db 输出）。"""
    from . import translations as trans

    card_type = raw.get("$type", "")
    is_item = card_type == "TCardItem"
    is_skill = card_type == "TCardSkill"

    loc = raw.get("Localization") or {}
    title_text = loc.get("Title", {}).get("Text", "") or raw.get("InternalName", "")
    title_key  = loc.get("Title", {}).get("Key", "")
    name_zh = zh_name or trans.get_zh(title_text) or (trans.get_zh_by_key(title_key) if title_key else "") or title_text
    name_en = title_text

    size_label = {"Small": "小", "Medium": "中", "Large": "大", "Small Large": "小/大"}.get(
        raw.get("Size", ""), raw.get("Size", ""))
    type_label = {"TCardItem": "物品", "TCardSkill": "技能"}.get(card_type, "")
    starting_tier = raw.get("StartingTier", "Bronze")
    heroes = "、".join(HERO_ZH.get(h, h) for h in (raw.get("Heroes") or [])) or "通用"
    tags = [TAG_ZH.get(t, t) for t in (raw.get("Tags") or [])]

    out = []
    header = f"📦 {name_zh}"
    if name_en and name_en != name_zh:
        header += f"（{name_en}）"
    out.append(header)

    meta = f"类型:{type_label}  尺寸:{size_label}  起始品质:{TIER_ZH.get(starting_tier, starting_tier)}  英雄:{heroes}"
    out.append(meta)
    if tags:
        out.append("标签: " + " ".join(tags))

    # 按 tier 展示 tooltips
    tier_order = [t for t in ("Bronze", "Silver", "Gold", "Diamond", "Legendary")
                  if t in (raw.get("Tiers") or {})]
    abilities = raw.get("Abilities") or {}
    auras = raw.get("Auras") or {}

    if tier_order:
        out.append("─")
        # 合并相同内容的 tier（避免重复展示）
        prev_block = None
        prev_tiers: list[str] = []
        def flush(tiers_list, block):
            label = "/".join(TIER_ZH.get(t, t) for t in tiers_list)
            out.append(f"[{label}] " + "  ".join(block))

        for tn in tier_order:
            tier_attrs = build_tier_attrs(raw, tn)
            lines: list[str] = []
            cd = tier_attrs.get("CooldownMax")
            if cd:
                lines.append(f"冷却{ms_to_s(cd)}s")
            # AmmoMax 不会自动出现在 tooltip 中；单独展示以避免不同品质被误合并。
            ammo = tier_attrs.get("AmmoMax")
            if ammo is not None:
                lines.append(f"弹药{int(ammo)}")
            multicast = tier_attrs.get("Multicast", 1)
            if multicast and multicast > 1:
                lines.append(f"多重x{int(multicast)}")
            # 主 tooltips
            for t in loc.get("Tooltips") or []:
                tip_cond = t.get("TooltipCondition")
                if tip_cond and tip_cond not in (None, "None"):
                    continue
                txt = (t.get("Content") or {}).get("Text", "")
                if txt:
                    # 先取中文模板（保留占位符），再渲染数值
                    zh_tpl = trans.get_tooltip_zh(txt) or txt
                    zh_tpl = annotate_implicit_ability_attributes(zh_tpl, abilities)
                    rendered = render_tooltip(zh_tpl, abilities, auras, tier_attrs)
                    lines.append(rendered)
            if lines == prev_block:
                prev_tiers.append(tn)
            else:
                if prev_block is not None:
                    flush(prev_tiers, prev_block)
                prev_block = lines
                prev_tiers = [tn]
        if prev_block is not None:
            flush(prev_tiers, prev_block)

    # Quest
    quests = raw.get("Quests") or []
    if quests:
        quest_tips = get_quest_tooltips(raw, starting_tier, db_path=db_path)
        if quest_tips:
            out.append("─")
            out.append("任务:")
            for q in quest_tips:
                reward_str = "  ".join(q["reward_tooltips"]) if q["reward_tooltips"] else "（升级效果）"
                out.append(f"  ✦ {q['condition']} → {reward_str}")

    # 附魔
    enchs = raw.get("Enchantments") or {}
    if enchs:
        out.append("─")
        out.append("附魔效果:")
        for enc_key, enc_data in enchs.items():
            enc_name = ENC_ZH.get(enc_key, enc_key)
            tips = get_enchant_tooltips(raw, enc_key)
            if tips:
                out.append(f"  [{enc_name}] " + "  ".join(tips))
            else:
                out.append(f"  [{enc_name}]")

    return "\n".join(out)


def query_raw_by_name(name: str, db_path: "str | Path") -> dict | None:
    """从 GameData.db 按名称查卡牌原始数据（支持 InternalName 或 Localization.Title.Text）。
    返回原始 JSON dict，找不到返回 None。
    """
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT Data FROM cards").fetchall()
    conn.close()
    name_lower = name.strip().lower()
    for (data,) in rows:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        try:
            d = json.loads(data)
        except Exception:
            continue
        internal = d.get("InternalName", "").lower()
        loc_title = (d.get("Localization") or {}).get("Title", {}).get("Text", "").lower()
        if name_lower in (internal, loc_title):
            return d
    return None


class GameDataClient:
    """从 GameData.db 读取并转换为 howbazaar 兼容格式"""

    def __init__(self, db_path: "str | Path"):
        self.db_path = Path(db_path)
        self._items: list[dict] = []
        self._skills: list[dict] = []
        self._monsters: list[dict] = []      # Boss/怪物
        self._pedestals: list[dict] = []     # 附魔台
        self._combats: list[dict] = []       # 战斗遭遇
        # id -> raw data 索引（用于 monster 手牌反查）
        self._item_by_id: dict[str, dict] = {}

    def load(self) -> None:
        """加载并转换数据"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"GameData.db 不存在: {self.db_path}")

        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        # 加载 cards 表
        cur.execute("SELECT Data FROM cards")
        rows = cur.fetchall()

        # 加载 monsters 表
        cur.execute("SELECT Data FROM monsters")
        monster_rows = cur.fetchall()

        conn.close()

        # 处理 cards
        items: list[dict] = []
        skills: list[dict] = []
        pedestals: list[dict] = []
        combats: list[dict] = []
        raw_items: dict[str, dict] = {}  # id -> raw data

        for (data,) in rows:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                d = json.loads(data)
            except Exception:
                continue

            card_type = d.get("$type")
            if card_type == "TCardItem":
                converted = convert_item_to_howbazaar_format(d)
                items.append(converted)
                raw_items[d.get("Id", "")] = converted  # 保存转换后的物品
            elif card_type == "TCardSkill":
                skills.append(convert_skill_to_howbazaar_format(d))
            elif card_type == "TCardEncounterPedestal":
                pedestals.append(self._convert_pedestal(d))
            elif card_type == "TCardEncounterCombat":
                combats.append(d)  # 先保存原始数据，等 monsters 加载后再处理

        # 处理 monsters，关联手牌物品名
        monsters: list[dict] = []
        for (data,) in monster_rows:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            try:
                d = json.loads(data)
            except Exception:
                continue
            monsters.append(self._convert_monster(d, raw_items))

        self._items = items
        self._skills = skills
        self._monsters = monsters
        self._pedestals = pedestals
        self._item_by_id = raw_items
        # 战斗遭遇关联 monster
        self._combats = [self._convert_combat(c) for c in combats]

        print(f"[GameDataClient] 已加载 {len(items)} 物品, {len(skills)} 技能, "
              f"{len(monsters)} Boss, {len(pedestals)} 附魔台, {len(combats)} 战斗遭遇")

    def _convert_monster(self, d: dict, item_by_id: dict) -> dict:
        """转换 monster 数据"""
        attrs = d.get("Player", {}).get("Attributes", {})
        hand = d.get("Player", {}).get("Hand", {})
        hand_items = hand.get("Items", [])

        # 把 TemplateId 转换成物品名
        items_in_hand = []
        for inst in hand_items:
            tid = inst.get("TemplateId", "")
            tier = inst.get("Tier", "")
            ench = inst.get("EnchantmentType")
            item = item_by_id.get(tid)
            name = item.get("name", tid) if item else tid
            items_in_hand.append({
                "name": name,
                "tier": tier,
                "enchantment": ench,
            })

        return {
            "id": d.get("Id", ""),
            "name": d.get("InternalName", "Unknown"),
            "health": attrs.get("HealthMax", 0),
            "level": attrs.get("Level", 0),
            "prestige": attrs.get("Prestige", 0),
            "items": items_in_hand,
        }

    def _convert_pedestal(self, d: dict) -> dict:
        """转换附魔台数据"""
        loc = d.get("Localization", {})
        name = loc.get("Title", {}).get("Text", d.get("InternalName", ""))
        desc = loc.get("Description", {}).get("Text", "") if loc.get("Description") else ""
        return {
            "id": d.get("Id", ""),
            "name": name,
            "internal_name": d.get("InternalName", ""),
            "tier": d.get("StartingTier", ""),
            "heroes": d.get("Heroes", []),
            "description": desc,
        }

    def _convert_combat(self, d: dict) -> dict:
        """转换战斗遭遇数据"""
        loc = d.get("Localization", {})
        name = loc.get("Title", {}).get("Text", d.get("InternalName", ""))
        combatant = d.get("CombatantType", {})
        monster_id = combatant.get("MonsterTemplateId", "")
        level = combatant.get("Level", 0)
        return {
            "id": d.get("Id", ""),
            "name": name,
            "internal_name": d.get("InternalName", ""),
            "tier": d.get("StartingTier", ""),
            "heroes": d.get("Heroes", []),
            "monster_id": monster_id,
            "level": level,
            "gold": d.get("RewardCombatGold", 0),
            "xp": d.get("RewardCombatXp", 0),
            "sandstorm": d.get("SandstormEnabled", False),
        }

    def items(self) -> list[dict]:
        return self._items

    def skills(self) -> list[dict]:
        return self._skills

    def monsters(self) -> list[dict]:
        return self._monsters

    def pedestals(self) -> list[dict]:
        return self._pedestals

    def combats(self) -> list[dict]:
        return self._combats

