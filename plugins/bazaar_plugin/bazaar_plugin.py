from . import bazaardb_client as bdb
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
        # 精简模式群组
        self._compact_path = PROJECT_ROOT / 'data' / 'bz_compact_groups.json'
        self._compact_groups: set = set()
        if self._compact_path.exists():
            import json as _j2
            try:
                self._compact_groups = set(str(x) for x in _j2.loads(self._compact_path.read_text(encoding='utf-8')).get('groups', []))
            except Exception:
                pass
        # 指令开关
        self._cmd_switch_path = PROJECT_ROOT / 'data' / 'bz_cmd_switch.json'
        self._disabled_cmds: set = set()
        if self._cmd_switch_path.exists():
            import json as _j
            try:
                self._disabled_cmds = set(_j.loads(self._cmd_switch_path.read_text(encoding='utf-8')).get('disabled', []))
            except Exception:
                pass
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
        # === 管理员指令开关 ===
        if sub == "admin":
            user_id = getattr(event, "user_id", 0)
            if not ADMIN_QQ or str(user_id) != str(ADMIN_QQ):
                return "[巴扎] 只有管理员能使用 admin 指令"
            import json as _j
            parts2 = arg.split()
            action = parts2[0] if parts2 else "status"
            if action == "status":
                if self._disabled_cmds:
                    lines = ["🔒 已禁用的指令:"]
                    for c in sorted(self._disabled_cmds):
                        lines.append(f"  · {c}")
                else:
                    lines = ["✅ 所有指令均已启用"]
                return chr(10).join(lines)
            if action == "disable" and len(parts2) >= 2:
                cmd = parts2[1].lower()
                self._disabled_cmds.add(cmd)
                self._cmd_switch_path.write_text(
                    _j.dumps({"disabled": list(self._disabled_cmds)}, ensure_ascii=False),
                    encoding="utf-8")
                return f"🔒 已禁用指令: {cmd}"
            if action == "enable" and len(parts2) >= 2:
                cmd = parts2[1].lower()
                self._disabled_cmds.discard(cmd)
                self._cmd_switch_path.write_text(
                    _j.dumps({"disabled": list(self._disabled_cmds)}, ensure_ascii=False),
                    encoding="utf-8")
                return f"✅ 已启用指令: {cmd}"
            if action == "compact":
                import json as _jc
                if len(parts2) < 2:
                    return "用法:\n  #bz admin compact <群号>\n  #bz admin compact <群号> off\n  #bz admin compact list"
                if parts2[1] == "list":
                    if self._compact_groups:
                        return "📋 精简模式群组:\n" + chr(10).join(f"  · {g}" for g in sorted(self._compact_groups))
                    return "📋 暂无群组开启精简模式"
                gid = str(parts2[1])
                if len(parts2) >= 3 and parts2[2] == "off":
                    self._compact_groups.discard(gid)
                    self._compact_path.write_text(_jc.dumps({"groups": list(self._compact_groups)}, ensure_ascii=False), encoding="utf-8")
                    return f"✅ 群 {gid} 已关闭精简模式"
                self._compact_groups.add(gid)
                self._compact_path.write_text(_jc.dumps({"groups": list(self._compact_groups)}, ensure_ascii=False), encoding="utf-8")
                return f"✅ 群 {gid} 已开启精简模式"
            return "用法:\n  #bz admin status\n  #bz admin disable <指令>\n  #bz admin enable <指令>\n  #bz admin compact <群号> [off]\n  #bz admin compact list"

        # === 指令开关检查 ===
        if sub in self._disabled_cmds:
            return f"[巴扎] 指令 {sub} 当前已关闭"

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

        if sub in {"db", "数据库", "card", "卡牌"}:
            if not arg:
                return "用法: #bz db <卡牌名>  (支持中英文，查 bazaardb.gg 数据)"
            return await self._cmd_db(arg)

        if sub in {"runs", "阵容", "run"}:
            return await self._cmd_runs(arg)

        if sub in {"winrate", "胜率"}:
            return await self._cmd_winrate(arg, event)

        if sub in {"topcard", "胜率卡", "职业胜率"}:
            return await self._cmd_topcard(arg, event)

        if sub in {"setphase", "切换阶段"}:
            return await self._cmd_setphase(arg, event)

        if sub in {"alias", "别名"}:
            return await self._cmd_alias(arg)

        if sub in {"partner", "搭档"}:
            return await self._cmd_partner(arg, event)

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
            import base64
            from pathlib import Path
            img_b64 = "base64://" + base64.b64encode(Path(img_path).read_bytes()).decode()
            if is_private:
                user_id = getattr(event, "user_id", 0)
                await self.api.post_private_msg(user_id=user_id, image=img_b64)
            else:
                group_id = getattr(event, "group_id", 0)
                await self.api.post_group_msg(group_id=group_id, image=img_b64)
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
            import base64
            from pathlib import Path
            img_b64 = "base64://" + base64.b64encode(Path(img_path).read_bytes()).decode()
            if is_private:
                user_id = getattr(event, "user_id", 0)
                await self.api.post_private_msg(user_id=user_id, image=img_b64)
            else:
                group_id = getattr(event, "group_id", 0)
                await self.api.post_group_msg(group_id=group_id, image=img_b64)
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

    # ===== runs 查询 =====
    async def _cmd_partner(self, arg: str, event=None) -> str:
        from .runs_query import get_client
        import re as _re

        if not arg:
            return (
                "🤝 卡牌最佳搭档查询\n\n"
                "用法: #bz partner <卡牌> [--days N]\n\n"
                "示例:\n"
                "  #bz partner 火炮阵列\n"
                "  #bz partner 火炮阵列 --days 7"
            )

        try:
            client = get_client()
        except Exception as e:
            return f"[巴扎] partner 初始化失败: {e}"

        days = None
        days_m = _re.search(r'--days\s+(\d+)', arg)
        if days_m:
            days = int(days_m.group(1))
            arg = arg[:days_m.start()] + arg[days_m.end():]
            arg = arg.strip()

        all_phases = '--all-phases' in arg
        if all_phases:
            arg = arg.replace('--all-phases', '').strip()

        card = arg.strip()
        if not card:
            return "[巴扎] 请指定卡牌名称"

        result = client.partner(card=card, days=days, all_phases=all_phases)

        if result["not_found"]:
            return f"[巴扎] 找不到卡牌「{card}」，请确认名称"

        card_name = result["card_name"]
        by_winrate = result["by_winrate"]
        by_appear = result["by_appear"]
        target_total = result["target_total"]

        title_parts = [card_name]
        if days:
            title_parts.append(f"近{days}天")

        if not by_winrate and not by_appear:
            return f"🤝 {card_name} 最佳搭档\n\n暂无满足条件的搭档数据（需至少50次共现）"

        # 精简模式
        group_id = str(getattr(event, "group_id", 0) or 0)
        if group_id in self._compact_groups:
            wr_names = " > ".join(p["name"] for p in by_winrate)
            ap_names = " > ".join(p["name"] for p in by_appear)
            return f"胜率榜: {wr_names}\n组合榜: {ap_names}"

        medals = ["🥇", "🥈", "🥉"]
        lines = [f"🤝 {' | '.join(title_parts)}（含该卡共 {target_total} 局）", ""]

        lines.append("📈 胜率榜 TOP3")
        for i, p in enumerate(by_winrate):
            lines.append(
                f"{medals[i]} {p['name']}  "
                f"10胜率 {p['rate']*100:.1f}%  ({p['ten_win']}/{p['total']} 局)"
            )

        lines.append("")
        lines.append("🔗 组合率榜 TOP3")
        for i, p in enumerate(by_appear):
            lines.append(
                f"{medals[i]} {p['name']}  "
                f"组合率 {p['appear_rate']*100:.1f}%  ({p['total']}/{target_total} 局)"
            )

        lines.append("")
        lines.append("💡 #bz partner <卡牌> [--days N]")
        return "\n".join(lines)


    async def _cmd_alias(self, arg: str) -> str:
        import json as _json
        from pathlib import Path as _Path
        import sys as _sys

        alias_file = _Path("/opt/qiubot/data/bz_aliases.json")

        def _load():
            if alias_file.exists():
                try:
                    return _json.loads(alias_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            return {"cards": {}, "heroes": {}}

        def _save(data):
            alias_file.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            mod = _sys.modules.get("plugins.bazaar_plugin.runs_query")
            if mod and hasattr(mod, "_client"):
                mod._client = None

        arg = (arg or "").strip()

        if not arg or arg == "list":
            data = _load()
            cards = data.get("cards", {})
            heroes = data.get("heroes", {})
            if not cards and not heroes:
                return "暂无自定义别名\n\n用法:\n  #bz alias <别名> <卡牌名>\n  #bz alias hero <别名> <英雄名>\n  #bz alias del <别名>\n  #bz alias list"
            lines = ["📋 自定义别名列表"]
            if cards:
                lines.append("\n🃏 卡牌别名：")
                for a, r in sorted(cards.items()):
                    lines.append(f"  {a} → {r}")
            if heroes:
                lines.append("\n🦸 英雄别名：")
                for a, r in sorted(heroes.items()):
                    lines.append(f"  {a} → {r}")
            return "\n".join(lines)

        parts = arg.split()

        if parts[0] == "del":
            if len(parts) < 2:
                return "用法: #bz alias del <别名>"
            target = parts[1]
            data = _load()
            removed = False
            for kind in ("cards", "heroes"):
                if target in data[kind]:
                    del data[kind][target]
                    removed = True
            if removed:
                _save(data)
                return f"已删除别名「{target}」\n\n💡 用法：\n  #bz alias <别名> <卡牌名>\n  #bz alias hero <别名> <英雄名>\n  #bz alias del <别名>\n  #bz alias list"

        if parts[0] == "hero":
            if len(parts) < 3:
                return "用法: #bz alias hero <别名> <英雄名>"
            alias = parts[1]
            real = " ".join(parts[2:])
            from .runs_query import get_client, HERO_ZH_TO_EN
            client = get_client()
            resolved = client.resolve_hero(real)
            if not resolved:
                valid = "、".join(sorted(set(HERO_ZH_TO_EN.keys())))
                return f"未识别的英雄「{real}」\n有效英雄名: {valid}"
            data = _load()
            data["heroes"][alias] = real
            _save(data)
            hero_map = {"Vanessa": "海盗", "Dooley": "工程师", "Mak": "法师",
                        "Pygmalien": "猪", "Stelle": "机甲", "Jules": "吸血鬼", "Karnok": "兽人"}
            return f"英雄别名已设置: {alias} → {real}（{hero_map.get(resolved, resolved)}）\n\n💡 用法：\n  #bz alias <别名> <卡牌名>\n  #bz alias hero <别名> <英雄名>\n  #bz alias del <别名>\n  #bz alias list"

  #bz alias <别名> <卡牌名>
  #bz alias hero <别名> <英雄名>
  #bz alias del <别名>
  #bz alias list" + "

  #bz alias <别名> <卡牌名>
  #bz alias hero <别名> <英雄名>
  #bz alias del <别名>
  #bz alias list"

        if len(parts) < 2:
            return "用法: #bz alias <别名> <卡牌名>"
        alias = parts[0]
        real = " ".join(parts[1:])
        from .runs_query import get_client
        client = get_client()
        ids = client.find_card_ids(real)
        if not ids:
            return f"找不到卡牌「{real}」，请确认卡牌名称"
        en_name = client.translate_name(real)
        zh_name = client.get_zh_name(en_name)
        display = zh_name if zh_name != en_name else real
        data = _load()
        data["cards"][alias] = real
        _save(data)
        return f"卡牌别名已设置: {alias} → {display}\n\n💡 用法：\n  #bz alias <别名> <卡牌名>\n  #bz alias hero <别名> <英雄名>\n  #bz alias del <别名>\n  #bz alias list"

  #bz alias <别名> <卡牌名>
  #bz alias hero <别名> <英雄名>
  #bz alias del <别名>
  #bz alias list" + "

  #bz alias <别名> <卡牌名>
  #bz alias hero <别名> <英雄名>
  #bz alias del <别名>
  #bz alias list"


    async def _cmd_winrate(self, arg: str, event=None) -> str:
        from .runs_query import get_client
        import re as _re

        if not arg:
            return (
                "📊 卡牌10胜率查询\n\n"
                "用法: #bz winrate <卡牌> [+<卡牌2>] [英雄] [--days N]\n\n"
                "示例:\n"
                "  #bz winrate 火炮阵列\n"
                "  #bz winrate 火炮阵列+赛博铁尺\n"
                "  #bz winrate 火炮阵列 海盗\n"
                "  #bz winrate 火炮阵列 --days 3"
            )

        try:
            client = get_client()
        except Exception as e:
            return f"[巴扎] winrate 初始化失败: {e}"

        days = None
        days_m = _re.search(r'--days\s+(\d+)', arg)
        if days_m:
            days = int(days_m.group(1))
            arg = arg[:days_m.start()] + arg[days_m.end():]
            arg = arg.strip()

        all_phases = '--all-phases' in arg
        if all_phases:
            arg = arg.replace('--all-phases', '').strip()

        hero = None
        cards = []
        parts = arg.split()
        for part in parts:
            resolved = client.resolve_hero(part)
            if resolved and not hero:
                hero = resolved
            else:
                for card in part.split('+'):
                    card = card.strip()
                    if card:
                        cards.append(card)

        if not cards:
            return "[巴扎] 请指定至少一张卡牌，例如: #bz winrate 火炮阵列"

        result = client.winrate(cards=cards, hero=hero, days=days, all_phases=all_phases)

        not_found = result.get('not_found', [])
        if not_found and not result['total']:
            return f"[巴扎] 找不到卡牌: {', '.join(not_found)}"

        card_str = '+'.join(result['card_names']) if result['card_names'] else '+'.join(cards)
        hero_map = {'Vanessa': '海盗', 'Dooley': '工程师', 'Mak': '法师',
                    'Pygmalien': '猪', 'Stelle': '机甲', 'Jules': '吸血鬼', 'Karnok': '兽人'}
        hero_zh = hero_map.get(hero, hero) if hero else None

        title_parts = [card_str]
        if hero_zh:
            title_parts.append(hero_zh)
        if days:
            title_parts.append(f"近{days}天")

        total = result['total']
        ten_win = result['ten_win']
        rate = result['rate']

        if total == 0:
            return f"📊 {' | '.join(title_parts)}\n\n数据库中暂无包含该卡牌的记录"

        # 精简模式
        group_id = str(getattr(event, "group_id", 0) or 0)
        if group_id in self._compact_groups:
            return f"{card_str}: {total}局/{rate*100:.1f}%"

        lines = [
            f"📊 {' | '.join(title_parts)}",
            "",
            f"10胜率：{rate*100:.1f}%",
            f"10胜局数：{ten_win}",
            f"含该卡总局数：{total}",
        ]
        if not_found:
            lines.append(f"⚠️ 未找到卡牌: {', '.join(not_found)}")

        lines.append("")
        lines.append("💡 #bz winrate <卡牌> [+卡牌2] [英雄] [--days N]")

        return '\n'.join(lines)

    async def _cmd_topcard(self, arg: str, event=None) -> str:
        from .runs_query import get_client
        import re as _re

        hero_zh_map = {
            'Vanessa': '海盗/凡妮莎', 'Dooley': '工程师/杜利',
            'Mak': '法师/马克', 'Pygmalien': '猪/皮格',
            'Stelle': '机甲/斯黛拉', 'Jules': '吸血鬼/朱尔斯',
            'Karnok': '兽人/卡诺克', 'The Dragons': '双龙',
        }
        all_heroes = list(hero_zh_map.keys())

        if not arg:
            hero_list = '  '.join(
                f"{v.split('/')[0]}({k})" for k, v in hero_zh_map.items()
            )
            return (
                "📊 职业胜率卡 Top N 查询\n\n"
                "用法: #bz topcard <职业> [N] [--days D]\n\n"
                "示例:\n"
                "  #bz topcard 海盗\n"
                "  #bz topcard Vanessa 10\n"
                "  #bz topcard 机甲 5 --days 7\n\n"
                f"可选职业: {hero_list}"
            )

        try:
            client = get_client()
        except Exception as e:
            return f"[巴扎] topcard 初始化失败: {e}"

        # 解析 --days
        days = None
        days_m = _re.search(r'--days\s+(\d+)', arg)
        if days_m:
            days = int(days_m.group(1))
            arg = (arg[:days_m.start()] + arg[days_m.end():]).strip()

        all_phases = '--all-phases' in arg
        if all_phases:
            arg = arg.replace('--all-phases', '').strip()

        # 解析职业和 top_n
        top_n = 5
        hero = None
        for part in arg.split():
            if part.isdigit():
                top_n = max(1, min(int(part), 30))
            elif not hero:
                hero = client.resolve_hero(part)

        if not hero:
            return f"[巴扎] 未识别职业，请输入职业名（如：海盗、Vanessa、机甲）"

        result = client.topcard(hero=hero, top_n=top_n, days=days, all_phases=all_phases)

        hero_zh = hero_zh_map.get(hero, hero)
        title_parts = [f"{hero_zh}", f"Top {top_n} 胜率卡"]
        if days:
            title_parts.append(f"近{days}天")

        total_runs = result['total_runs']
        top = result['top']

        if total_runs == 0:
            return f"📊 {'  |  '.join(title_parts)}\n\n暂无数据"

        lines = [
            f"📊 {'  |  '.join(title_parts)}",
            f"(本赛季共 {total_runs} 局)",
            "",
        ]
        for i, item in enumerate(top, 1):
            bar_len = int(item['rate'] * 20)
            bar = '█' * bar_len + '░' * (20 - bar_len)
            lines.append(
                f"{i}. {item['name_zh']}"
            )
            lines.append(
                f"   {bar} {item['rate']*100:.1f}%"
            )
            lines.append(
                f"   {item['ten_win']}胜 / {item['total']}局"
            )

        lines.append("")
        lines.append("💡 #bz topcard <职业> [N] [--days D]")

        return '\n'.join(lines)

    async def _cmd_setphase(self, arg: str, event=None) -> str:
        """切换当前赛季阶段，仅管理员可用"""
        import re as _re
        import sqlite3 as _sqlite3
        from datetime import datetime as _dt
        from .data_client import CURRENT_SEASON_ID

        # 权限检查
        admin_qq = self._admin_qq()
        sender_qq = str(getattr(event, "user_id", 0) or 0)
        if admin_qq and sender_qq not in admin_qq:
            return "[巴扎] 仅管理员可切换阶段"

        phase = arg.strip()
        if not phase:
            from .data_client import CURRENT_PHASE
            return (
                f"📋 当前阶段: {CURRENT_PHASE}\n\n"
                "用法: #bz setphase <阶段>\n"
                "示例: #bz setphase 17.2"
            )

        # 格式校验：必须是 数字.数字
        if not _re.match(r'^\d+\.\d+$', phase):
            return "[巴扎] 阶段格式错误，应为 赛季.阶段 如 17.2"

        season = int(phase.split('.')[0])
        if season != CURRENT_SEASON_ID:
            return f"[巴扎] 阶段赛季({season})与当前赛季({CURRENT_SEASON_ID})不符"

        try:
            # 更新 data_client.py 中的 CURRENT_PHASE
            dc_path = __import__('pathlib').Path(__file__).parent / 'data_client.py'
            dc_text = dc_path.read_text(encoding='utf-8')
            import re as re2
            dc_new = re2.sub(
                r'CURRENT_PHASE = "[^"]*"',
                f'CURRENT_PHASE = "{phase}"',
                dc_text
            )
            dc_path.write_text(dc_new, encoding='utf-8')

            # 记录到 phases 表
            conn = _sqlite3.connect('/opt/qiubot/data/bazaar_runs.db')
            conn.execute(
                'INSERT OR IGNORE INTO phases (season, phase, start_time) VALUES (?,?,?)',
                [CURRENT_SEASON_ID, phase, _dt.utcnow().isoformat()]
            )
            conn.commit()
            conn.close()

            # 热重载本模块的 CURRENT_PHASE（让进程内立即生效）
            import importlib
            import plugins.bazaar_plugin.data_client as _dc
            importlib.reload(_dc)

            return (
                f"✅ 已切换至阶段 {phase}\n"
                f"新收集的 runs 将标记为 {phase}\n"
                f"查询命令默认使用 {phase} 数据"
            )
        except Exception as e:
            return f"[巴扎] 切换阶段失败: {e}"



    async def _cmd_db(self, arg: str) -> str:
        """查询卡牌数据（优先本地 GameData.db，fallback bazaardb.gg）"""
        from . import gamedata_client as gdc
        from . import translations as trans
        from . import card_image_helper as cih
        import asyncio, os, re
        loop = asyncio.get_event_loop()

        # 解析参数
        show_enchants = '--enchants' in arg or '-e' in arg
        query_arg = re.sub(r'--enchants|-e', '', arg).strip()
        
        en_name = query_arg.strip()
        if trans.has_chinese(query_arg):
            candidates = trans.search_zh(arg, limit=3)
            if candidates:
                en_name = candidates[0]

        from dotenv import load_dotenv; load_dotenv()
        db_path = os.getenv("GAMEDATA_DB", "")
        raw = None
        if db_path:
            try:
                raw = await loop.run_in_executor(None, gdc.query_raw_by_name, en_name, db_path)
                if raw is None and en_name != arg.strip():
                    raw = await loop.run_in_executor(None, gdc.query_raw_by_name, arg.strip(), db_path)
            except Exception as e:
                print(f"[bz db] GameData.db 查询失败: {e}")

        if raw is not None:
            zh = trans.get_zh(en_name) or ""
            text = gdc.format_card_from_raw(raw, zh_name=zh, db_path=db_path, show_enchants=show_enchants)
            card_id = raw.get("Id", "")
            art_url = cih.get_art_url(card_id=card_id, internal_name=en_name, size="artLarge")
            if art_url:
                return f"[CQ:image,file={art_url}]\n" + text
            return text

        from . import bazaardb_client as bdb
        try:
            card = await loop.run_in_executor(None, bdb.query_card_by_name, query_arg)
        except Exception as e:
            return f"[巴扎] 查询失败: {e}"
        if card is None:
            results_item = await loop.run_in_executor(None, bdb.search_cards, arg, "item")
            results_skill = await loop.run_in_executor(None, bdb.search_cards, arg, "skill")
            results = (results_item or []) + (results_skill or [])
            if not results:
                return f"未找到「{arg}」，请检查卡牌名称"
            if len(results) == 1:
                card = results[0]
            else:
                names = "、".join(r.get("name", "?") for r in results[:5])
                return f"找到多个结果: {names}\n请用更精确的名字重试，如: #bz db 万剑之王"
        text = bdb.format_card(card, show_enchants=show_enchants)
        art_url = card.get("ArtLarge") or card.get("Art", "")
        if art_url:
            return f"[CQ:image,file={art_url}]\n" + text
        return text


    async def _cmd_runs(self, arg: str) -> str:
        from .runs_query import get_client
        import re as _re

        try:
            client = get_client()
        except Exception as e:
            return f"[巴扎] runs 查询初始化失败: {e}"

        raw_cmd = "#bz runs " + arg if arg else "#bz runs"

        if not arg:
            help_text = (
                "📋 BazaarDB 阵容查询\n\n"
                "用法: #bz runs [英雄] [卡牌+卡牌] [--days N] [-pN]\n\n"
                "示例:\n"
                "  #bz runs 海盗 — 查海盗阵容\n"
                "  #bz runs 火炮阵列 — 查含火炮阵列的阵容\n"
                "  #bz runs 海盗 赛博铁尺+火炮阵列 — 组合查询\n"
                "  #bz runs 工程师 --days 3 — 近3天\n"
                "  #bz runs 海盗 -p2 — 第2页\n"
                "  #bz runs 海盗 --wins 7 — 查7胜以上（默认10胜）"
            )
            return help_text

        # 解析 --days
        days = None
        days_m = _re.search(r'--days\s+(\d+)', arg)
        if days_m:
            days = int(days_m.group(1))
            arg = arg[:days_m.start()] + arg[days_m.end():]
            arg = arg.strip()

        # 解析 -pN
        page = 1
        page_m = _re.search(r'-p(\d+)', arg)
        if page_m:
            page = int(page_m.group(1))
            arg = arg[:page_m.start()] + arg[page_m.end():]
            arg = arg.strip()

        # 解析 --legend
        # 解析 --wins（最低胜场，默认10）
        min_wins = 10
        wins_m = _re.search(r'--wins\s+(\d+)', arg)
        if wins_m:
            min_wins = int(wins_m.group(1))
            arg = arg[:wins_m.start()] + arg[wins_m.end():]
            arg = arg.strip()

        # 解析英雄和卡牌
        hero = None
        cards = []

        parts = arg.split()
        for part in parts:
            resolved = client.resolve_hero(part)
            if resolved and not hero:
                hero = resolved
            else:
                for card in part.split('+'):
                    card = card.strip()
                    if card:
                        cards.append(card)

        result = client.query(hero=hero, cards=cards or None, days=days, min_wins=min_wins, page=page)

        desc_parts = []
        if hero:
            hero_zh = {'Vanessa': '海盗', 'Dooley': '工程师', 'Mak': '法师',
                       'Pygmalien': '猪', 'Stelle': '机甲', 'Jules': '吸血鬼',
                       'Karnok': '兽人'}.get(hero, hero)
            desc_parts.append(hero_zh)
        if cards:
            desc_parts.append('+'.join(cards))
        if days:
            desc_parts.append(f"近{days}天")
        query_desc = ' '.join(desc_parts)

        return client.format_result(result, query_desc, raw_cmd)
