"""
anti_repeat_plugin.py — 复读禁言插件

逻辑：
- 全群同一条内容连续出现达到阈值（默认5次），触发禁言最新发送者
- 阈值之后每次继续触发，直到出现不同内容才归零
- 群管理员/群主可发指令调整阈值和禁言时长

指令（仅群管理员/群主）：
  /repeat threshold <n>   设置触发阈值（最少2）
  /repeat duration <n>    设置禁言时长（分钟）
  /repeat status          查看当前配置
"""

import json
import os
from collections import defaultdict

from ncatbot.plugin_system import NcatBotPlugin, on_message
from ncatbot.core.event import BaseMessageEvent

# 配置持久化路径
_CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anti_repeat_config.json")

# 默认配置
_DEFAULT_THRESHOLD = 5   # 触发禁言的连续复读次数
_DEFAULT_DURATION  = 1   # 禁言时长（分钟）


def _load_cfg() -> dict:
    if os.path.exists(_CFG_PATH):
        try:
            with open(_CFG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cfg(cfg: dict):
    with open(_CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class AntiRepeatPlugin(NcatBotPlugin):
    """复读禁言插件"""
    name    = "AntiRepeatPlugin"
    version = "1.0.0"

    async def on_load(self):
        # group_id -> {"last_msg": str, "count": int}
        self._state: dict[str, dict] = defaultdict(lambda: {"last_msg": None, "count": 0})
        # group_id -> {"threshold": int, "duration": int}
        self._cfg: dict[str, dict] = _load_cfg()
        print(f"[{self.name}] 已加载 v{self.version}")

    def _get_threshold(self, group_id: str) -> int:
        return self._cfg.get(group_id, {}).get("threshold", _DEFAULT_THRESHOLD)

    def _get_duration(self, group_id: str) -> int:
        return self._cfg.get(group_id, {}).get("duration", _DEFAULT_DURATION)

    def _is_group_admin(self, event: BaseMessageEvent) -> bool:
        role = getattr(getattr(event, "sender", None), "role", None)
        return role in ("admin", "owner")

    @on_message
    async def handle(self, event: BaseMessageEvent):
        # 仅处理群消息
        if getattr(event, "message_type", None) != "group":
            return

        group_id = str(getattr(event, "group_id", ""))
        user_id  = str(getattr(event, "user_id", ""))
        text     = (event.raw_message or "").strip()

        if not text or not group_id:
            return

        # ── 管理员指令 ──────────────────────────────────────────
        if text.startswith("/repeat ") and self._is_group_admin(event):
            await self._handle_cmd(event, group_id, text)
            return

        # ── 复读检测 ────────────────────────────────────────────
        state = self._state[group_id]

        if text == state["last_msg"]:
            state["count"] += 1
        else:
            state["last_msg"] = text
            state["count"]    = 1

        threshold = self._get_threshold(group_id)
        if state["count"] >= threshold:
            duration_min = self._get_duration(group_id)
            duration_sec = duration_min * 60
            try:
                await event.ban(duration_sec)
                sender_name = (
                    getattr(event.sender, "card", None)
                    or getattr(event.sender, "nickname", None)
                    or user_id
                )
                await self.api.post_group_msg(
                    group_id=int(group_id),
                    text=f"🔇 {sender_name} 因复读被禁言 {duration_min} 分钟。"
                )
            except Exception as e:
                print(f"[{self.name}] 禁言失败 group={group_id} user={user_id}: {e}")

    async def _handle_cmd(self, event: BaseMessageEvent, group_id: str, text: str):
        parts = text.split()
        # /repeat threshold <n>
        if len(parts) == 3 and parts[1] == "threshold":
            try:
                n = int(parts[2])
                if n < 2:
                    await event.reply("阈值最小为 2。")
                    return
                self._cfg.setdefault(group_id, {})["threshold"] = n
                _save_cfg(self._cfg)
                await event.reply(f"✅ 已设置复读阈值为 {n} 次。")
            except ValueError:
                await event.reply("用法：/repeat threshold <次数>")

        # /repeat duration <n>
        elif len(parts) == 3 and parts[1] == "duration":
            try:
                n = int(parts[2])
                if n < 1:
                    await event.reply("禁言时长最小为 1 分钟。")
                    return
                self._cfg.setdefault(group_id, {})["duration"] = n
                _save_cfg(self._cfg)
                await event.reply(f"✅ 已设置禁言时长为 {n} 分钟。")
            except ValueError:
                await event.reply("用法：/repeat duration <分钟>")

        # /repeat status
        elif len(parts) == 2 and parts[1] == "status":
            t = self._get_threshold(group_id)
            d = self._get_duration(group_id)
            state = self._state[group_id]
            await event.reply(
                f"📋 复读禁言配置\n"
                f"触发阈值：{t} 次\n"
                f"禁言时长：{d} 分钟\n"
                f"当前计数：{state['count']} 次\n"
                f"当前内容：{repr(state['last_msg'])}"
            )
        else:
            await event.reply(
                "用法：\n"
                "/repeat threshold <次数>\n"
                "/repeat duration <分钟>\n"
                "/repeat status"
            )
