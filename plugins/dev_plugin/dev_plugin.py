"""
dev_plugin — QQ 机器人二次开发工作流插件
"""
import asyncio
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from ncatbot.plugin_system import NcatBotPlugin, on_message
from ncatbot.core.event import BaseMessageEvent

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
MODEL    = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
ADMIN_QQ = os.getenv("BAZAAR_ADMIN_QQ", "ADMIN_QQ_NUMBER").strip()

TIMEOUT_CHAT    = 86400
TIMEOUT_APPROVE = 86400
TIMEOUT_DEVELOP = 36000

CQ_AT_ANY_RE = re.compile(r"\[CQ:at,qq=\d+[^\]]*\]")
CQ_ANY_RE    = re.compile(r"\[CQ:[^\]]+\]")

MODE_PRIVATE = "private"
MODE_GROUP   = "group"

S_CHOOSING_MODE    = "CHOOSING_MODE"
S_CHATTING         = "CHATTING"
S_CONFIRMING       = "CONFIRMING"
S_PENDING_APPROVAL = "PENDING_APPROVAL"
S_DEVELOPING       = "DEVELOPING"
S_PENDING_DEPLOY   = "PENDING_DEPLOY"

ANALYST_SYSTEM = (
    "你是一个 QQ 机器人需求分析师，帮助用户把模糊的功能想法变成清晰的开发需求。\n"
    "规则：\n"
    "- 每次只问一个最关键的问题，给出 2-4 个选项（数字标注），也允许用户自由描述\n"
    "- 当需求足够清晰时，输出 [READY] 然后跟需求摘要：\n\n"
    "[READY]\n"
    "功能名称：xxx\n"
    "触发方式：xxx\n"
    "功能描述：xxx\n"
    "输出内容：xxx\n"
    "注意事项：xxx（如有）\n\n"
    "语气友好简洁，用中文，不用 markdown。"
)


STATE_LABELS = {
    S_CHOOSING_MODE:    "选择沟通方式",
    S_CHATTING:         "需求沟通中",
    S_CONFIRMING:       "等待用户确认需求",
    S_PENDING_APPROVAL: "等待管理员审批",
    S_DEVELOPING:       "AI 开发中",
    S_PENDING_DEPLOY:   "等待管理员确认上线",
}


class DevRequest:
    def __init__(self, user_qq: str, group_id: Optional[str], init_text: str):
        self.user_qq      = user_qq
        self.group_id     = group_id
        self.init_text    = init_text
        self.state        = S_CHOOSING_MODE
        self.chat_mode    = MODE_PRIVATE
        self.history: list = []
        self.summary      = ""
        self.dev_result   = ""
        self.dev_log      = ""   # 开发过程摘要（实时更新）
        self.git_snapshot = ""
        self.created_at   = time.time()
        self.updated_at   = time.time()
        self.dev_start_at: float = 0.0  # 开发开始时间

    def touch(self):
        self.updated_at = time.time()

    def is_expired(self) -> bool:
        elapsed = time.time() - self.updated_at
        if self.state in (S_CHOOSING_MODE, S_CHATTING, S_CONFIRMING):
            return elapsed > TIMEOUT_CHAT
        if self.state == S_PENDING_APPROVAL:
            return elapsed > TIMEOUT_APPROVE
        return elapsed > TIMEOUT_DEVELOP


class DevPlugin(NcatBotPlugin):
    name    = "DevPlugin"
    version = "1.1.0"

    async def on_load(self):
        self._requests: dict = {}
        self._lock = asyncio.Lock()
        print("[DevPlugin] 已加载 v{}, 管理员={}".format(self.version, ADMIN_QQ))

    @on_message
    async def handle(self, event: BaseMessageEvent):
        raw  = event.raw_message or ""
        text = CQ_AT_ANY_RE.sub("", raw)
        text = CQ_ANY_RE.sub("", text).strip()
        if not text:
            return

        user_qq  = str(event.user_id)
        is_priv  = getattr(event, "message_type", None) == "private"
        group_id = str(getattr(event, "group_id", "") or "") if not is_priv else None

        if user_qq == ADMIN_QQ:
            if await self._admin_cmd(text, event, is_priv):
                return

        if re.match(r"^#dev\s*(help|帮助|\?)$", text, re.IGNORECASE):
            await event.reply(_help_text())
            return

        if re.match(r"^#dev\s*(status|进度|状态)$", text, re.IGNORECASE):
            async with self._lock:
                req = self._requests.get(user_qq)
            if not req or req.is_expired():
                await event.reply("你当前没有进行中的开发需求。\n发起需求：#dev <你的想法>")
            else:
                await event.reply(_status_text(req))
            return

        if re.match(r"^#dev\s+(?!cancel|list|help|帮助|\?)\S", text, re.IGNORECASE):
            init = text[len("#dev"):].strip()
            await self._start_request(event, user_qq, group_id, is_priv, init)
            return

        async with self._lock:
            req = self._requests.get(user_qq)
        if req and not req.is_expired():
            if is_priv:
                await self._on_reply(event, req, text, user_qq, is_priv=True)
            elif req.chat_mode == MODE_GROUP and group_id == req.group_id:
                await self._on_reply(event, req, text, user_qq, is_priv=False)

    async def _admin_cmd(self, text: str, event, is_priv: bool) -> bool:
        if re.match(r"^#dev\s+list$", text, re.IGNORECASE):
            async with self._lock:
                reqs = list(self._requests.items())
            if not reqs:
                await event.reply("当前没有进行中的开发需求。")
            else:
                lines = ["📋 进行中的需求："]
                for qq, r in reqs:
                    age = int((time.time() - r.created_at) / 60)
                    mode_tag = "群聊" if r.chat_mode == MODE_GROUP else "私聊"
                    lines.append("  QQ {} | {} | {} | {}min | {}".format(
                        qq, r.state, mode_tag, age, r.init_text[:20]))
                await event.reply("\n".join(lines))
            return True

        m = re.match(r"^#dev\s+cancel\s+(\d+)$", text, re.IGNORECASE)
        if m:
            target = m.group(1)
            async with self._lock:
                req = self._requests.pop(target, None)
            if req:
                await event.reply("✅ 已取消 QQ {} 的需求".format(target))
                await self.api.post_private_msg(
                    user_id=int(target), text="你的开发需求已被管理员取消。")
            else:
                await event.reply("未找到 QQ {} 的进行中需求".format(target))
            return True

        async with self._lock:
            approvals = [(qq, r) for qq, r in self._requests.items()
                         if r.state == S_PENDING_APPROVAL]
        if approvals and is_priv:
            if text.strip() == "同意":
                qq, req = approvals[-1]
                await self._approve(req, qq)
                return True
            m2 = re.match(r"^拒绝(.*)$", text.strip())
            if m2:
                reason = m2.group(1).strip() or "管理员未说明原因"
                qq, req = approvals[-1]
                await self._reject(req, qq, reason)
                return True

        async with self._lock:
            deploys = [(qq, r) for qq, r in self._requests.items()
                       if r.state == S_PENDING_DEPLOY]
        if deploys and is_priv:
            if text.strip() == "上线":
                qq, req = deploys[-1]
                await self._deploy(req, qq)
                return True
            if text.strip() == "取消":
                qq, req = deploys[-1]
                await self._deploy_cancel(req, qq)
                return True

        return False

    async def _start_request(self, event, user_qq, group_id, is_priv, init_text):
        async with self._lock:
            existing = self._requests.get(user_qq)
        if existing and not existing.is_expired():
            await event.reply(
                "你已有一个进行中的需求（{}），请先完成再提新需求。".format(existing.state))
            return

        req = DevRequest(user_qq=user_qq, group_id=group_id, init_text=init_text)
        async with self._lock:
            self._requests[user_qq] = req

        if is_priv:
            req.chat_mode = MODE_PRIVATE
            await self._begin_chatting(req, user_qq)
            return

        choose_msg = (
            "收到你的需求！请选择需求沟通方式：\n\n"
            "1️⃣  私聊我 — 一对一沟通，更快捷\n"
            "2️⃣  在群里讨论 — 集思广益，其他群友也能参与\n\n"
            "回复 1 或 2"
        )
        await event.reply(choose_msg)

    async def _on_reply(self, event, req: DevRequest, text: str, user_qq: str, is_priv: bool):
        req.touch()

        if req.state == S_CHOOSING_MODE:
            if text.strip() in ("1", "私聊", "私聊我"):
                req.chat_mode = MODE_PRIVATE
                await event.reply("好的，我私聊你继续沟通 👻")
                await self._begin_chatting(req, user_qq)
            elif text.strip() in ("2", "群聊", "群里"):
                req.chat_mode = MODE_GROUP
                await self._begin_chatting_group(req, user_qq)
            else:
                await event.reply("请回复 1（私聊）或 2（群聊）")
            return

        if req.state == S_CHATTING:
            req.history.append({"role": "user", "content": text})
            reply = await self._analyst(req)
            if "[READY]" in reply:
                summary = reply[reply.index("[READY]") + 7:].strip()
                req.summary = summary
                req.state   = S_CONFIRMING
                msg = "✅ 需求已整理：\n\n{}\n\n回复「确认」提交审批，或告诉我需要修改的地方。".format(summary)
                await self._send_to_user(req, user_qq, msg)
            else:
                req.history.append({"role": "assistant", "content": reply})
                await self._send_to_user(req, user_qq, reply)

        elif req.state == S_CONFIRMING:
            if text.strip() == "确认":
                req.state = S_PENDING_APPROVAL
                req.touch()
                admin_msg = (
                    "📬 新开发需求待审批\n"
                    "提交人：QQ {}\n"
                    "沟通方式：{}\n\n"
                    "{}\n\n"
                    "回复「同意」或「拒绝 [原因]」"
                ).format(user_qq, "群聊" if req.chat_mode == MODE_GROUP else "私聊", req.summary)
                await self.api.post_private_msg(user_id=int(ADMIN_QQ), text=admin_msg)
                await self._send_to_user(req, user_qq, "需求已提交，等待管理员审批 🕐")
            else:
                req.state = S_CHATTING
                req.history.append({"role": "user", "content": text})
                reply = await self._analyst(req)
                if "[READY]" in reply:
                    summary = reply[reply.index("[READY]") + 7:].strip()
                    req.summary = summary
                    req.state   = S_CONFIRMING
                    msg = "✅ 已更新需求：\n\n{}\n\n回复「确认」提交，或继续修改。".format(summary)
                    await self._send_to_user(req, user_qq, msg)
                else:
                    req.history.append({"role": "assistant", "content": reply})
                    await self._send_to_user(req, user_qq, reply)

    async def _begin_chatting(self, req: DevRequest, user_qq: str):
        req.state = S_CHATTING
        req.history.append({"role": "user", "content": req.init_text})
        first_reply = await self._analyst(req)
        req.history.append({"role": "assistant", "content": first_reply})
        intro = "👋 收到你的开发需求：\n「{}」\n\n{}".format(req.init_text, first_reply)
        await self.api.post_private_msg(user_id=int(user_qq), text=intro)

    async def _begin_chatting_group(self, req: DevRequest, user_qq: str):
        req.state = S_CHATTING
        req.history.append({"role": "user", "content": req.init_text})
        first_reply = await self._analyst(req)
        req.history.append({"role": "assistant", "content": first_reply})
        intro = "[CQ:at,qq={}] 👋 收到需求：\n「{}」\n\n{}".format(
            user_qq, req.init_text, first_reply)
        await self.api.post_group_msg(group_id=int(req.group_id), text=intro)

    async def _send_to_user(self, req: DevRequest, user_qq: str, text: str):
        if req.chat_mode == MODE_GROUP and req.group_id:
            msg = "[CQ:at,qq={}] {}".format(user_qq, text)
            await self.api.post_group_msg(group_id=int(req.group_id), text=msg)
        else:
            await self.api.post_private_msg(user_id=int(user_qq), text=text)

    async def _approve(self, req: DevRequest, user_qq: str):
        req.state = S_DEVELOPING
        req.dev_start_at = time.time()
        req.touch()
        await self.api.post_private_msg(user_id=int(ADMIN_QQ), text="✅ 已批准，开始开发...")
        await self._send_to_user(req, user_qq,
            "🎉 需求通过审批！AI 正在开发中，预计需要几分钟。\n随时发 #dev status 查看进度。")
        asyncio.create_task(self._run_dev(req, user_qq))

    async def _reject(self, req: DevRequest, user_qq: str, reason: str):
        async with self._lock:
            self._requests.pop(user_qq, None)
        await self.api.post_private_msg(
            user_id=int(ADMIN_QQ), text="✅ 已拒绝 QQ {} 的需求".format(user_qq))
        await self._send_to_user(req, user_qq,
            "❌ 需求未通过审批。\n原因：{}".format(reason))

    async def _run_dev(self, req: DevRequest, user_qq: str):
        snap = await asyncio.get_event_loop().run_in_executor(None, _git_snapshot)
        req.git_snapshot = snap

        # 启动定时推送任务（每2分钟告知用户开发还在进行）
        push_task = asyncio.create_task(self._dev_progress_push(req, user_qq))

        prompt = (
            "你是QiuBot项目开发者。根据需求文档，在 /opt/qiubot 项目里开发新功能。\n\n"
            "需求文档：\n{}\n\n"
            "项目路径：/opt/qiubot\n"
            "插件目录：/opt/qiubot/plugins/\n"
            "开发完成后输出 [DONE] 以及一句话说明改动。"
        ).format(req.summary)

        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _call_hermes, prompt),
                timeout=600
            )
        except asyncio.TimeoutError:
            result = "[TIMEOUT]"
        except Exception as e:
            result = "[ERROR] {}".format(e)
        finally:
            push_task.cancel()  # 开发结束，停止定时推送

        req.dev_result = result
        req.dev_log = result[:200].strip()  # 保存摘要供 status 查询
        req.touch()

        if "[DONE]" in result:
            done_msg = result[result.index("[DONE]") + 6:].strip().splitlines()[0]
            req.state = S_PENDING_DEPLOY
            admin_msg = (
                "🛠️ 开发完成！\n"
                "改动：{}\n"
                "提交人：QQ {}\n\n"
                "回复「上线」重启生效，或「取消」回滚。"
            ).format(done_msg, user_qq)
            await self.api.post_private_msg(user_id=int(ADMIN_QQ), text=admin_msg)
            await self._send_to_user(req, user_qq,
                "✅ 开发完成！\n改动内容：{}\n\n正在等待管理员确认上线，稍等片刻～".format(done_msg))
        else:
            await asyncio.get_event_loop().run_in_executor(
                None, _git_rollback, req.git_snapshot)
            async with self._lock:
                self._requests.pop(user_qq, None)
            await self.api.post_private_msg(
                user_id=int(ADMIN_QQ),
                text="❌ 开发失败，已自动回滚。\n错误：{}".format(result[:300]))
            await self._send_to_user(req, user_qq,
                "😞 开发遇到问题，代码已回滚，请稍后重新提交需求。")

    async def _dev_progress_push(self, req: DevRequest, user_qq: str):
        """开发过程中每2分钟主动推送一次进度。"""
        interval = 120  # 2分钟
        try:
            while True:
                await asyncio.sleep(interval)
                if req.state != S_DEVELOPING:
                    break
                elapsed = int((time.time() - req.dev_start_at) / 60)
                msg = "🛠️ AI 仍在开发中，已用时 {} 分钟...\n发 #dev status 查看详情。".format(elapsed)
                await self._send_to_user(req, user_qq, msg)
        except asyncio.CancelledError:
            pass

    async def _deploy(self, req: DevRequest, user_qq: str):
        req.touch()
        await asyncio.get_event_loop().run_in_executor(
            None, _git_commit_push, req.summary[:50])
        await asyncio.get_event_loop().run_in_executor(None, _restart_qiubot)
        async with self._lock:
            self._requests.pop(user_qq, None)
        await self.api.post_private_msg(
            user_id=int(ADMIN_QQ), text="✅ 已上线并重启 QiuBot，代码已推送到 GitHub。")
        await self._send_to_user(req, user_qq, "🚀 功能已上线！QiuBot 已重启，去群里试试吧～")
        if req.group_id:
            first_line = req.summary.splitlines()[0] if req.summary else "新功能"
            await self.api.post_group_msg(
                group_id=int(req.group_id),
                text="📢 新功能上线：{}\n（由 QQ {} 提需求）".format(first_line, user_qq))

    async def _deploy_cancel(self, req: DevRequest, user_qq: str):
        await asyncio.get_event_loop().run_in_executor(
            None, _git_rollback, req.git_snapshot)
        async with self._lock:
            self._requests.pop(user_qq, None)
        await self.api.post_private_msg(
            user_id=int(ADMIN_QQ), text="✅ 已取消，代码已回滚。")
        await self._send_to_user(req, user_qq, "需求已取消，代码已回滚。")

    async def _analyst(self, req: DevRequest) -> str:
        try:
            return await _call_claude(req.history, ANALYST_SYSTEM)
        except Exception as e:
            return "[AI 调用失败: {}]".format(e)


async def _call_claude(messages: list, system: str) -> str:
    url = "{}/v1/messages".format(BASE_URL)
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": system,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, headers=headers, json=payload)
        data = r.json()
    if r.status_code >= 400:
        raise RuntimeError("HTTP {}: {}".format(r.status_code, data.get("error", data)))
    content = data.get("content") or []
    return "\n".join(b["text"] for b in content if b.get("type") == "text").strip()


def _call_hermes(prompt: str) -> str:
    import shutil
    hermes_bin = Path.home() / ".local" / "bin" / "hermes"
    if not hermes_bin.exists():
        h = shutil.which("hermes")
        hermes_bin = Path(h) if h else None
    if not hermes_bin:
        return "[ERROR] 找不到 hermes"
    try:
        r = subprocess.run(
            [str(hermes_bin), "chat", "-q", prompt, "--yolo"],
            capture_output=True, text=True,
            timeout=580, cwd="/opt/qiubot"
        )
        return (r.stdout or "").strip() or "[hermes 无输出]"
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return "[ERROR] {}".format(e)


def _git_snapshot() -> str:
    try:
        subprocess.run(["git", "add", "-A"], cwd="/opt/qiubot", capture_output=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "snapshot: before dev"],
            cwd="/opt/qiubot", capture_output=True)
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd="/opt/qiubot", capture_output=True, text=True)
        return r.stdout.strip()
    except Exception as e:
        return "error:{}".format(e)


def _git_rollback(snapshot_hash: str):
    if not snapshot_hash or snapshot_hash.startswith("error:"):
        return
    try:
        subprocess.run(
            ["git", "reset", "--hard", snapshot_hash],
            cwd="/opt/qiubot", capture_output=True)
    except Exception:
        pass


def _git_commit_push(msg: str):
    try:
        subprocess.run(["git", "add", "-A"], cwd="/opt/qiubot", capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: {}".format(msg)],
            cwd="/opt/qiubot", capture_output=True)
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd="/opt/qiubot", capture_output=True, timeout=60)
    except Exception:
        pass


def _restart_qiubot():
    try:
        subprocess.run(
            ["sudo", "systemctl", "restart", "qiubot"],
            capture_output=True, timeout=30)
    except Exception:
        pass


def _help_text() -> str:
    return (
        "🤖 QiuBot 功能开发工作流\n"
        "━━━━━━━━━━━━━━\n"
        "任何群友都可以向机器人提交新功能需求，\n"
        "经过需求沟通和管理员审批后，\n"
        "由 AI 自动开发并上线到机器人。\n"
        "━━━━━━━━━━━━━━\n"
        "【发起需求】\n"
        "#dev <你的想法>\n"
        "例：#dev 我想要一个每日签到积分功能\n"
        "\n"
        "【选择沟通方式】\n"
        "1️⃣  私聊机器人 — 一对一高效沟通\n"
        "2️⃣  在群里讨论 — 集思广益，群友可参与\n"
        "\n"
        "【需求沟通】\n"
        "机器人会通过几轮对话澄清需求，\n"
        "每次给出选项，也可以自由描述。\n"
        "最后回复「确认」提交审批。\n"
        "\n"
        "【审批与开发】\n"
        "管理员审批通过后，AI 自动开发，\n"
        "开发中每2分钟会主动推送进度，\n"
        "完成后管理员确认上线，群里会播报。\n"
        "━━━━━━━━━━━━━━\n"
        "常用指令：\n"
        "#dev <想法>    发起需求\n"
        "#dev status   查看我的需求进度\n"
        "#dev help     查看本帮助\n"
        "━━━━━━━━━━━━━━\n"
        "注意事项：\n"
        "· 每人同时只能有一个进行中的需求\n"
        "· 管理员有权拒绝或取消任意需求\n"
        "· 开发失败会自动回滚，不影响现有功能"
    )


def _status_text(req: DevRequest) -> str:
    state_label = STATE_LABELS.get(req.state, req.state)
    elapsed_total = int((time.time() - req.created_at) / 60)
    lines = [
        "📋 我的开发需求进度",
        "━━━━━━━━━━━━━━",
        "需求：{}".format(req.init_text[:40] + ("..." if len(req.init_text) > 40 else "")),
        "状态：{} {}".format(_state_icon(req.state), state_label),
        "提交：{} 分钟前".format(elapsed_total),
    ]

    if req.state == S_DEVELOPING and req.dev_start_at:
        dev_elapsed = int((time.time() - req.dev_start_at) / 60)
        lines.append("开发耗时：{} 分钟".format(dev_elapsed))

    if req.summary and req.state not in (S_CHOOSING_MODE, S_CHATTING):
        first_line = req.summary.splitlines()[0] if req.summary else ""
        if first_line:
            lines.append("需求摘要：{}".format(first_line))

    if req.state == S_PENDING_DEPLOY and req.dev_log:
        lines.append("开发结果：{}".format(req.dev_log[:80]))

    lines.append("━━━━━━━━━━━━━━")

    next_step = {
        S_CHOOSING_MODE:    "回复 1 或 2 选择沟通方式",
        S_CHATTING:         "继续回答机器人的问题",
        S_CONFIRMING:       "回复「确认」提交审批，或继续修改",
        S_PENDING_APPROVAL: "等待管理员审批，无需操作",
        S_DEVELOPING:       "AI 正在开发，请耐心等待",
        S_PENDING_DEPLOY:   "等待管理员确认上线，无需操作",
    }.get(req.state, "")
    if next_step:
        lines.append("下一步：{}".format(next_step))

    return "\n".join(lines)


def _state_icon(state: str) -> str:
    return {
        S_CHOOSING_MODE:    "❓",
        S_CHATTING:         "💬",
        S_CONFIRMING:       "📝",
        S_PENDING_APPROVAL: "⏳",
        S_DEVELOPING:       "🛠️",
        S_PENDING_DEPLOY:   "✅",
    }.get(state, "•")
