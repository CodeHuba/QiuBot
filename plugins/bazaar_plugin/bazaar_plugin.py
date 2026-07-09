"""
大巴扎 (The Bazaar) QQ 群插件
- bz me <用户名>      mrmao 玩家信息
- bz item <名字>      物品百科
- bz skill <名字>     技能百科
- bz npc <名字>       商人百科
- bz day <1-10|event> 当日 encounter 列表
- bz boss <名字>      encounter 详情
- bz search <关键词>  跨物品/技能搜索
- bz status / refresh 缓存状态 / 强制刷新
"""
import asyncio
import os
import re
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from ncatbot.plugin_system import NcatBotPlugin, on_message
from ncatbot.core.event import BaseMessageEvent

from .data_client import BazaarDataClient
from . import matcher, formatter as fmt, subscriptions as subs, tooltip_translations as tt_trans
from . import chart as chart_mod
from . import history_chart as hist_chart_mod

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# 管理员 QQ（用于 /bz refresh），从环境变量读，未设置则禁用
ADMIN_QQ = os.getenv("BAZAAR_ADMIN_QQ", os.getenv("ROOT_QQ", "")).strip()

# CQ 码处理
CQ_AT_ANY_RE = re.compile(r"\[CQ:at,qq=\d+[^\]]*\]")
CQ_ANY_RE = re.compile(r"\[CQ:[^\]]+\]")

# 触发前缀：#bz（避免 /bz 触发QQ表情），同时保留中文别名
TRIGGER_RE = re.compile(r"^\s*(#bz\b\s*|[/／]\s*(巴扎|大巴扎)\b\s*)", re.IGNORECASE)

# 冷却（秒）
COOLDOWN_PLAYER = 10   # /bz me 同 user
COOLDOWN_DEFAULT = 3   # 其他指令同 user

# 单条回复最大字符数（兜底）
MAX_REPLY_LEN = 3500


class BazaarPlugin(NcatBotPlugin):
    name = "BazaarPlugin"
    version = "1.0.0"

    async def on_load(self):
        self.client = BazaarDataClient()
        self._cooldown: dict[tuple, float] = defaultdict(float)
        # 同步加载卡图映射（不依赖网络，立即可用）
        _tex_map_path = Path(__file__).resolve().parent / "cache" / "item_tex_map.json"
        if _tex_map_path.exists():
            import json as _json
            self._tex_map = _json.loads(_tex_map_path.read_text(encoding="utf-8"))
            print(f"[BazaarPlugin] 卡图映射加载: {len(self._tex_map)} 条")
        else:
            self._tex_map: dict = {}
        # 启动时异步加载（不阻塞插件 on_load 完成）
        asyncio.create_task(self._init_data())
        # 注册每日 10:00 推送任务
        self.add_scheduled_task(
            job_func=self._daily_watch_task,
            name="bazaar_daily_watch",
            interval="10:00",  # 每天 10:00
        )
        print(f"[{self.name}] 已加载 v{self.version}, 每日 10:00 推送已启用")

    async def _init_data(self):
        try:
            await self.client.bootstrap()
            s = self.client.status()
            print(f"[{self.name}] 数据就绪: items={s['items']} skills={s['skills']} merchants={s['merchants']} days={s['encounter_days']}")
            # 同步 tooltip 翻译缓存的版本号
            combined_ver = s["versions"].get("items", "") + "|" + s["versions"].get("skills", "")
            tt_trans.set_version(combined_ver)
            # 加载卡图映射
            _tex_map_path = Path(__file__).resolve().parent / "cache" / "item_tex_map.json"
            if _tex_map_path.exists():
                import json as _json
                self._tex_map = _json.loads(_tex_map_path.read_text(encoding="utf-8"))
                print(f"[{self.name}] 卡图映射加载: {len(self._tex_map)} 条")
        except Exception as e:
            print(f"[{self.name}] 数据加载失败: {e}")

    # ===== 主入口 =====
    @on_message
    async def handle(self, event: BaseMessageEvent):
        raw = event.raw_message or ""
        # 剥掉 @CQ 码（群里被 @ 也允许，但纯文本要带 /bz）
        text = CQ_AT_ANY_RE.sub("", raw).strip()
        # 不剥其他 CQ（图片之类）→ 直接看是否以前缀开头
        m = TRIGGER_RE.match(text)
        if not m:
            return
        body = text[m.end():].strip()
        # 把残留的 CQ 码全清掉
        body = CQ_ANY_RE.sub("", body).strip()

        if not body:
            await event.reply(fmt.format_help())
            return

        # 解析子命令
        parts = body.split(maxsplit=1)
        sub = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        user_id = getattr(event, "user_id", 0)

        # 冷却检查
        cd_key = (user_id, sub)
        cd_window = COOLDOWN_PLAYER if sub == "me" else COOLDOWN_DEFAULT
        now = time.time()
        if (now - self._cooldown[cd_key]) < cd_window:
            remain = int(cd_window - (now - self._cooldown[cd_key]))
            await event.reply(f"指令冷却中，{remain}s 后再试")
            return

        try:
            reply = await self._dispatch(sub, arg, event)
        except Exception as e:
            print(f"[{self.name}] 处理 bz {sub} 失败: {e}")
            reply = f"[巴扎] 处理失败: {e}"

        # reply=None 表示子命令已自行发送（如图片），仍需记录冷却
        self._cooldown[cd_key] = now
        if reply:
            if len(reply) > MAX_REPLY_LEN:
                reply = reply[:MAX_REPLY_LEN] + "\n...(已截断)"
            await event.reply(reply)

    # ===== 子命令分发 =====
    async def _dispatch(self, sub: str, arg: str, event: BaseMessageEvent) -> str:
        if sub in {"help", "帮助", "?"}:
            return fmt.format_help()

        if sub == "status":
            return fmt.format_status(self.client.status())

        if sub == "refresh":
            user_id = getattr(event, "user_id", 0)
            if not ADMIN_QQ or str(user_id) != str(ADMIN_QQ):
                return "[巴扎] 只有管理员能强制刷新"
            try:
                await self.client.refresh(force=True)
                return "✅ 巴扎百科已强制刷新\n" + fmt.format_status(self.client.status())
            except Exception as e:
                return f"[巴扎] 刷新失败: {e}"

        if sub == "me":
            if not arg:
                return "用法: #bz me <用户名>"
            return await self._cmd_player(arg)

        if sub == "stat":
            if not arg:
                return "用法: #bz stat <用户名>"
            return await self._cmd_player_stat(arg, event)

        if sub in {"history", "hist", "历史"}:
            if not arg:
                return "用法: #bz history <用户名> [--cb]"
            # 解析 --cb 色盲模式标志
            colorblind = "--cb" in arg
            username_h = arg.replace("--cb", "").strip()
            if not username_h:
                return "用法: #bz history <用户名> [--cb]"
            return await self._cmd_player_history(username_h, event, colorblind=colorblind)

        if sub == "item":
            return await self._cmd_item(arg, event=event)

        if sub == "skill":
            return await self._cmd_skill(arg, event=event)

        if sub == "npc":
            return self._cmd_npc(arg)

        if sub == "day":
            return self._cmd_day(arg)

        if sub == "boss":
            return self._cmd_boss(arg)

        if sub == "search":
            return self._cmd_search(arg)

        if sub == "watch":
            if not arg:
                return "用法: #bz watch <用户名>"
            return await self._cmd_watch(event, arg)

        if sub == "unwatch":
            if not arg:
                return "用法: #bz unwatch <用户名>"
            return await self._cmd_unwatch(event, arg)

        if sub == "watchlist":
            return self._cmd_watchlist(event)

        if sub == "testpush":
            user_id = getattr(event, "user_id", 0)
            if not ADMIN_QQ or str(user_id) != str(ADMIN_QQ):
                return "[巴扎] 只有管理员能触发测试推送"
            return await self._cmd_testpush(event)

        return f"未知子命令: {sub}\n\n" + fmt.format_help()

    # ===== 各子命令 =====
    async def _cmd_player(self, username: str) -> str:
        # 用户名安全：只允许常见字符 + 中文
        if len(username) > 30 or any(c in username for c in "<>\"'\\"):
            return "[巴扎] 用户名格式不合法"
        try:
            data = await self.client.get_player(username)
        except Exception as e:
            return f"[巴扎] 查询失败: {e}"
        return fmt.format_player(username, data)

    async def _cmd_player_stat(self, username: str, event: BaseMessageEvent) -> str | None:
        if len(username) > 30 or any(c in username for c in "<>\"'\\"):
            return "[巴扎] 用户名格式不合法"
        try:
            data = await self.client.get_player_stat(username)
        except Exception as e:
            return f"[巴扎] 查询失败: {e}"

        rh = data.get("ratingHistory") or []
        if not rh:
            return f"📊 {username} · 本赛季无记录"

        # 生成图表
        try:
            img_path = await asyncio.get_event_loop().run_in_executor(
                None, chart_mod.generate_stat_chart, username, rh
            )
        except Exception as e:
            print(f"[{self.name}] 图表生成失败，fallback 文字: {e}")
            return fmt.format_player_stat(username, data)

        # 发图片（群聊/私聊分别处理）
        is_private = getattr(event, "message_type", None) == "private"
        try:
            if is_private:
                user_id = getattr(event, "user_id", 0)
                await self.api.post_private_msg(user_id=user_id, image=img_path)
            else:
                group_id = getattr(event, "group_id", 0)
                await self.api.post_group_msg(group_id=group_id, image=img_path)
        except Exception as e:
            print(f"[{self.name}] 图片发送失败，fallback 文字: {e}")
            return fmt.format_player_stat(username, data)

        return None  # 图已发，handle 不再 reply

    async def _cmd_player_history(self, username: str, event: BaseMessageEvent, colorblind: bool = False) -> str | None:
        if len(username) > 30 or any(c in username for c in "<>\"'\\"):
            return "[巴扎] 用户名格式不合法"
        try:
            data = await self.client.get_player_stat(username)
        except Exception as e:
            return f"[巴扎] 查询失败: {e}"

        rh = data.get("ratingHistory") or []
        if not rh:
            return f"📊 {username} · 本赛季无记录"

        try:
            img_path = await asyncio.get_event_loop().run_in_executor(
                None, hist_chart_mod.generate_history_chart, username, rh, colorblind
            )
        except Exception as e:
            print(f"[{self.name}] history图表生成失败: {e}")
            return f"[巴扎] 图表生成失败: {e}"

        is_private = getattr(event, "message_type", None) == "private"
        try:
            if is_private:
                user_id = getattr(event, "user_id", 0)
                await self.api.post_private_msg(user_id=user_id, image=img_path)
            else:
                group_id = getattr(event, "group_id", 0)
                await self.api.post_group_msg(group_id=group_id, image=img_path)
        except Exception as e:
            print(f"[{self.name}] history图片发送失败: {e}")
            return f"[巴扎] 图片发送失败: {e}"

        return None

    def _ensure_loaded(self) -> str | None:
        if not self.client.items() or not self.client.skills():
            return "[巴扎] 数据还在加载中，稍等几秒再试"
        return None

    async def _cmd_item(self, arg: str, event: BaseMessageEvent | None = None) -> str:
        guard = self._ensure_loaded()
        if guard:
            return guard
        if not arg:
            return "用法: #bz item <名字>  例: #bz item lugnut"
        with_ench = False
        if arg.endswith(" +ench") or arg.endswith(" +enchant"):
            with_ench = True
            arg = arg.rsplit("+", 1)[0].strip()
        ent, candidates = matcher.find_one(arg, self.client.items())
        if ent:
            # 翻译 tooltips
            translated = await self._translate_tooltips(ent)
            return fmt.format_item(ent, with_all_enchants=with_ench, translated_tooltips=translated)
        if candidates:
            return fmt.format_candidates(candidates, "物品")
        return f"找不到物品『{arg}』"

    async def _cmd_skill(self, arg: str, event: BaseMessageEvent | None = None) -> str:
        guard = self._ensure_loaded()
        if guard:
            return guard
        if not arg:
            return "用法: #bz skill <名字>  例: #bz skill above"
        ent, candidates = matcher.find_one(arg, self.client.skills())
        if ent:
            # 翻译 tooltips
            translated = await self._translate_tooltips(ent)
            return fmt.format_skill(ent, translated_tooltips=translated)
        if candidates:
            return fmt.format_candidates(candidates, "技能")
        return f"找不到技能『{arg}』"

    async def _send_card_image(self, item_name: str, event: BaseMessageEvent):
        """发卡图，失败静默"""
        try:
            tex_name = self._tex_map.get(item_name)
            if not tex_name:
                return
            img_path = Path(__file__).resolve().parent / "cache" / "card_images" / (tex_name + ".png")
            if not img_path.exists():
                return
            # ncatbot image= 参数需要 base64:// 格式
            import base64
            img_b64 = "base64://" + base64.b64encode(img_path.read_bytes()).decode()
            is_private = getattr(event, "message_type", None) == "private"
            if is_private:
                uid = getattr(event, "user_id", 0)
                await self.api.post_private_msg(user_id=uid, image=img_b64)
            else:
                gid = getattr(event, "group_id", 0)
                await self.api.post_group_msg(group_id=gid, image=img_b64)
        except Exception as e:
            import traceback
            with open("/tmp/bz_card_err.txt", "a") as f:
                f.write(repr(e) + "\n" + traceback.format_exc() + "\n")

    async def _translate_tooltips(self, entity: dict) -> dict:
        """收集所有 tier + 附魔 的 tooltips，并发翻译，返回 {英文: 中文} 字典。"""
        name = entity.get("name") or ""
        tiers = entity.get("tiers") or {}
        tasks = []
        keys = []

        # tier tooltips
        for tier in ("Bronze", "Silver", "Gold", "Diamond", "Legendary"):
            info = tiers.get(tier) or {}
            for t in (info.get("tooltips") or []):
                if t:
                    tasks.append(tt_trans.translate_tooltip(t, name, tier))
                    keys.append(t)

        # 附魔 tooltips
        for ench in (entity.get("enchantments") or []):
            ench_type = ench.get("type") or ""
            for t in (ench.get("tooltips") or []):
                if t:
                    tasks.append(tt_trans.translate_tooltip(t, name, f"enchant_{ench_type}"))
                    keys.append(t)

        if not tasks:
            return {}
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = {}
        for k, r in zip(keys, results):
            if isinstance(r, str):
                out[k] = r
        return out

    def _cmd_npc(self, arg: str) -> str:
        guard = self._ensure_loaded()
        if guard:
            return guard
        if not arg:
            return "用法: #bz npc <名字>"
        ent, candidates = matcher.find_one(arg, self.client.merchants())
        if ent:
            return fmt.format_merchant(ent)
        if candidates:
            return fmt.format_candidates(candidates, "商人")
        return f"找不到商人『{arg}』"

    def _cmd_day(self, arg: str) -> str:
        guard = self._ensure_loaded()
        if guard:
            return guard
        if not arg:
            return "用法: #bz day <1-10|event>"
        day_data = self.client.get_encounter_day(arg.strip())
        if not day_data:
            avail = [str(d.get("day")) for d in self.client.encounter_days()]
            return f"找不到 day『{arg}』,可选: {', '.join(avail)}"
        return fmt.format_day(day_data)

    def _cmd_boss(self, arg: str) -> str:
        guard = self._ensure_loaded()
        if guard:
            return guard
        if not arg:
            return "用法: #bz boss <名字>"
        card = self.client.find_encounter_by_name(arg)
        if not card:
            return f"找不到 encounter『{arg}』"
        return fmt.format_boss(card)

    def _cmd_search(self, arg: str) -> str:
        guard = self._ensure_loaded()
        if guard:
            return guard
        if not arg or len(arg) < 2:
            return "用法: #bz search <关键词>  (至少 2 个字符)"
        items = matcher.find_matches(arg, self.client.items(), limit=20)
        skills = matcher.find_matches(arg, self.client.skills(), limit=20)
        return fmt.format_search(arg, items, skills)

    # ===== 订阅相关 =====
    def _ensure_group(self, event: BaseMessageEvent) -> tuple[int | None, str | None]:
        """只允许群聊订阅。返回 (group_id, error_msg)。"""
        is_private = getattr(event, "message_type", None) == "private"
        if is_private:
            return None, "[巴扎] #bz watch 只能在 QQ 群里使用"
        gid = getattr(event, "group_id", None)
        if not gid:
            return None, "[巴扎] 拿不到群号,请在群里使用"
        return int(gid), None

    async def _cmd_watch(self, event: BaseMessageEvent, username: str) -> str:
        gid, err = self._ensure_group(event)
        if err:
            return err
        if len(username) > 30 or any(c in username for c in "<>\"'\\"):
            return "[巴扎] 用户名格式不合法"
        # 验证用户存在(直接查一次,失败就不让订阅)
        try:
            await self.client.get_player(username)
        except Exception as e:
            return f"[巴扎] 玩家『{username}』查询失败,无法订阅: {e}"

        added = subs.add_subscription(f"group:{gid}", username)
        if not added:
            return f"📌 本群已订阅『{username}』,不用重复订阅"
        cur = subs.get_subscriptions(f"group:{gid}")
        return f"✅ 本群已订阅『{username}』,每天 10:00 推送昨日变化\n当前订阅 {len(cur)} 人"

    async def _cmd_unwatch(self, event: BaseMessageEvent, username: str) -> str:
        gid, err = self._ensure_group(event)
        if err:
            return err
        removed = subs.remove_subscription(f"group:{gid}", username)
        if not removed:
            return f"❎ 本群没有订阅『{username}』"
        cur = subs.get_subscriptions(f"group:{gid}")
        return f"🗑️ 已取消订阅『{username}』,本群剩余 {len(cur)} 人"

    def _cmd_watchlist(self, event: BaseMessageEvent) -> str:
        gid, err = self._ensure_group(event)
        if err:
            return err
        cur = subs.get_subscriptions(f"group:{gid}")
        if not cur:
            return "📭 本群还没订阅任何玩家\n用 #bz watch <用户名> 添加"
        lines = [f"📋 本群订阅 ({len(cur)} 人):"]
        for u in cur:
            lines.append(f"  · {u}")
        lines.append("")
        lines.append("每天 10:00 推送 24h 分数变化")
        return "\n".join(lines)

    async def _cmd_testpush(self, event: BaseMessageEvent) -> str:
        """管理员立即触发一次推送(只推当前群)。"""
        gid, err = self._ensure_group(event)
        if err:
            return err
        cur = subs.get_subscriptions(f"group:{gid}")
        if not cur:
            return "📭 本群没有订阅,无法推送"
        
        # 直接构造报告并发送
        text = await self._build_daily_report(cur)
        if not text:
            return "❌ 构造播报失败"
        
        try:
            await self.api.post_group_msg(group_id=gid, text=text)
            return f"✅ 已推送播报到本群 ({len(cur)} 人)"
        except Exception as e:
            return f"❌ 推送失败: {e}"

    # ===== 每日推送任务 =====
    async def _daily_watch_task(self):
        """每天 10:00 触发,遍历所有群订阅,推送 24h 变化。"""
        all_subs = subs.get_all_subscriptions()
        if not all_subs:
            print(f"[{self.name}] 每日推送: 无订阅,跳过")
            return
        print(f"[{self.name}] 每日推送启动,共 {len(all_subs)} 个聊天")

        # 按群推送
        for chat_key, usernames in all_subs.items():
            if not chat_key.startswith("group:"):
                continue  # 只推群,私聊不支持
            try:
                gid = int(chat_key.split(":", 1)[1])
            except Exception:
                continue
            text = await self._build_daily_report(usernames)
            if not text:
                continue
            try:
                await self.api.post_group_msg(group_id=gid, text=text)
                print(f"[{self.name}] 已推送到群 {gid} ({len(usernames)} 人)")
            except Exception as e:
                print(f"[{self.name}] 推送群 {gid} 失败: {e}")
            # 避免短时间内连发
            await asyncio.sleep(1)

    async def _build_daily_report(self, usernames: list[str]) -> str:
        """构造一份每日播报。"""
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"📊 大巴扎每日播报 · {now_str}"]
        lines.append("━━━━━━━━━━━━━━")

        for u in usernames:
            try:
                data = await self.client.get_player_stat(u)
            except Exception as e:
                lines.append(f"\n{u}: ❌ {e}")
                continue
            block = fmt.format_daily_diff(u, data)
            lines.append("")
            lines.append(block)

        return "\n".join(lines)
