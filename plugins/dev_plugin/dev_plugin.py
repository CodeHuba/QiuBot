"""
dev_plugin — QQ 机器人二次开发工作流插件

流程：IDLE → CHATTING → CONFIRMING → PENDING_APPROVAL → DEVELOPING → PENDING_DEPLOY → DONE

指令：
  群里/私聊: #dev <需求描述>        发起需求
  私聊: 确认                       用户确认需求摘要
  私聊(管理员): 同意 / 拒绝 [原因]  审批需求
  私聊(管理员): 上线 / 取消         确认部署
  #dev cancel <QQ>                 管理员强制取消
  #dev list                        管理员查看进行中需求
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

API_KEY  = os.getenv("ANTHROPIC_API_KEY", "").strip()
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
MODEL    = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
ADMIN_QQ = os.getenv("BAZAAR_ADMIN_QQ", "ADMIN_QQ_NUMBER").strip()

TIMEOUT_CHAT    = 86400   # 需求沟通 24h
TIMEOUT_APPROVE = 86400   # 管理员审批 24h
TIMEOUT_DEVELOP = 36000   # 开发 10h

CQ_AT_ANY_RE = re.compile(r"\[CQ:at,qq=\d+[^\]]*\]")
CQ_ANY_RE    = re.compile(r"\[CQ:[^\]]+\]")

S_CHATTING         = "CHATTING"
S_CONFIRMING       = "CONFIRMING"
S_PENDING_APPROVAL = "PENDING_APPROVAL"
S_DEVELOPING       = "DEVELOPING"
S_PENDING_DEPLOY   = "PENDING_DEPLOY"

ANALYST_SYSTEM = (
    "你是一个 QQ 机器人需求分析师，帮助用户把模糊的功能想法变成清晰的开发需求。\n"
    "规则：\n"
    "- 每次只问一个最关键的问题，给出 2-4 个选项（数字标注），也允许用户自由描述\n"
    "- 当需求足够清晰（了解功能目标、触发方式、输出内容），输出 [READY] 然后跟需求摘要：\n\n"
    "[READY]\n"
    "功能名称：xxx\n"
    "触发方式：xxx\n"
    "功能描述：xxx\n"
    "输出内容：xxx\n"
    "注意事项：xxx（如有）\n\n"
    "语气友好简洁，用中文，不用 markdown。"
)


class DevRequest:
    def __init__(self, user_qq: str, group_id: Optional[str], init_text: str):
        self.user_qq      = user_qq
        self.group_id     = group_id
        self.init_text    = init_text
        self.state        = S_CHATTING
        self.history: list[dict] = []
        self.summary      = ""
        self.dev_result   = ""
        self.git_snapshot = ""
        self.created_at   = time.time()
        self.updated_at   = time.time()

    def touch(self):
        self.updated_at = time.time()

    def is_expired(self) -> bool:
        elapsed = time.time() - self.updated_at
        if self.state in (S_CHATTING, S_CONFIRMING):
            return elapsed > TIMEOUT_CHAT
        if self.state == S_PENDING_APPROVAL:
            return elapsed > TIMEOUT_APPROVE
        return elapsed > TIMEOUT_DEVELOP


class DevPlugin(NcatBotPlugin):
    name    = "DevPlugin"
    version = "1.0.0"

    async def on_load(self):
        self._requests: dict[str, DevRequest] = {}
        self._lock = asyncio.Lock()
        print("[DevPlugin] 已加载 v{}, 管理员={}".format(self.version, ADMIN_QQ))

    # ── 主入口 ──────────────────────────────────
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

        # 管理员专属指令
        if user_qq == ADMIN_QQ:
            if await self._admin_cmd(text, event, is_priv):
                return

        # #dev help
        if re.match(r"^#dev\s*(help|帮助|\?)$", text, re.IGNORECASE):
            await event.reply(_help_text())
            return

        # 发起新需求
        if re.match(r"^#dev\s+(?!cancel|list|help|帮助|\?)\S", text, re.IGNORECASE):
            init = text[len("#dev"):].strip()
            await self._start_request(event, user_qq, group_id, is_priv, init)
            return

        # 进行中需求的私聊回复
        if is_priv:
            async with self._lock:
                req = self._requests.get(user_qq)
            if req and not req.is_expired():
                await self._on_user_reply(event, req, text, user_qq)

    # ── 管理员指令 ───────────────────────────────
    async def _admin_cmd(self, text: str, event, is_priv: bool) -> bool:
        # #dev list
        if re.match(r"^#dev\s+list$", text, re.IGNORECASE):
            async with self._lock:
                reqs = list(self._requests.items())
            if not reqs:
                await event.reply("当前没有进行中的开发需求。")
            else:
                lines = ["📋 进行中的需求："]
                for qq, r in reqs:
                    age = int((time.time() - r.created_at) / 60)
                    lines.append("  QQ {} | {} | {}min | {}".format(
                        qq, r.state, age, r.init_text[:25]))
                await event.reply("\n".join(lines))
            return True

        # #dev cancel <QQ>
        m = re.match(r"^#dev\s+cancel\s+(\d+)$", text, re.IGNORECASE)
        if m:
            target = m.group(1)
            async with self._lock:
                req = self._requests.pop(target, None)
            if req:
                await event.reply("✅ 已取消 QQ {} 的需求".format(target))
                await self.api.post_private_msg(
                    user_id=int(target),
                    text="你的开发需求已被管理员取消。")
            else:
                await event.reply("未找到 QQ {} 的进行中需求".format(target))
            return True

        # 审批：同意 / 拒绝
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

        # 部署：上线 / 取消
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

    # ── 发起需求 ─────────────────────────────────
    async def _start_request(self, event, user_qq, group_id, is_priv, init_text):
        async with self._lock:
            existing = self._requests.get(user_qq)
        if existing and not existing.is_expired():
            await event.reply(
                "你已有一个进行中的需求（{}），请先完成再提新需求。".format(existing.state))
            return

        req = DevRequest(user_qq=user_qq, group_id=group_id, init_text=init_text)
        req.history.append({"role": "user", "content": init_text})
        async with self._lock:
            self._requests[user_qq] = req

        if not is_priv:
            await event.reply("收到需求！我已私聊你进行详细沟通 👻")

        first_reply = await self._analyst(req)
        intro = "👋 收到你的开发需求：\n「{}」\n\n{}".format(init_text, first_reply)
        await self.api.post_private_msg(user_id=int(user_qq), text=intro)

    # ── 用户私聊回复 ─────────────────────────────
    async def _on_user_reply(self, event, req: DevRequest, text: str, user_qq: str):
        req.touch()

        if req.state == S_CHATTING:
            req.history.append({"role": "user", "content": text})
            reply = await self._analyst(req)

            if "[READY]" in reply:
                summary = reply[reply.index("[READY]") + 7:].strip()
                req.summary = summary
                req.state   = S_CONFIRMING
                msg = "✅ 需求已整理：\n\n{}\n\n回复「确认」提交审批，或告诉我需要修改的地方。".format(summary)
                await self.api.post_private_msg(user_id=int(user_qq), text=msg)
            else:
                req.history.append({"role": "assistant", "content": reply})
                await self.api.post_private_msg(user_id=int(user_qq), text=reply)

        elif req.state == S_CONFIRMING:
            if text.strip() == "确认":
                req.state = S_PENDING_APPROVAL
                req.touch()
                admin_msg = (
                    "📬 新开发需求待审批\n"
                    "提交人：QQ {}\n\n"
                    "{}\n\n"
                    "回复「同意」或「拒绝 [原因]」"
                ).format(user_qq, req.summary)
                await self.api.post_private_msg(user_id=int(ADMIN_QQ), text=admin_msg)
                await self.api.post_private_msg(
                    user_id=int(user_qq), text="需求已提交，等待管理员审批 🕐")
            else:
                # 用户想修改
                req.state = S_CHATTING
                req.history.append({"role": "user", "content": text})
                reply = await self._analyst(req)
                if "[READY]" in reply:
                    summary = reply[reply.index("[READY]") + 7:].strip()
                    req.summary = summary
                    req.state   = S_CONFIRMING
                    msg = "✅ 已更新需求：\n\n{}\n\n回复「确认」提交，或继续修改。".format(summary)
                    await self.api.post_private_msg(user_id=int(user_qq), text=msg)
                else:
                    req.history.append({"role": "assistant", "content": reply})
                    await self.api.post_private_msg(user_id=int(user_qq), text=reply)

    # ── 审批通过 ─────────────────────────────────
    async def _approve(self, req: DevRequest, user_qq: str):
        req.state = S_DEVELOPING
        req.touch()
        await self.api.post_private_msg(user_id=int(ADMIN_QQ), text="✅ 已批准，开始开发...")
        await self.api.post_private_msg(
            user_id=int(user_qq),
            text="🎉 需求通过审批！正在开发中，完成后通知你。")
        asyncio.create_task(self._run_dev(req, user_qq))

    # ── 审批拒绝 ─────────────────────────────────
    async def _reject(self, req: DevRequest, user_qq: str, reason: str):
        async with self._lock:
            self._requests.pop(user_qq, None)
        await self.api.post_private_msg(
            user_id=int(ADMIN_QQ),
            text="✅ 已拒绝 QQ {} 的需求".format(user_qq))
        await self.api.post_private_msg(
            user_id=int(user_qq),
            text="❌ 需求未通过审批。\n原因：{}".format(reason))

    # ── 执行开发 ─────────────────────────────────
    async def _run_dev(self, req: DevRequest, user_qq: str):
        snap = await asyncio.get_event_loop().run_in_executor(None, _git_snapshot)
        req.git_snapshot = snap

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

        req.dev_result = result
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
        else:
            await asyncio.get_event_loop().run_in_executor(
                None, _git_rollback, req.git_snapshot)
            async with self._lock:
                self._requests.pop(user_qq, None)
            await self.api.post_private_msg(
                user_id=int(ADMIN_QQ),
                text="❌ 开发失败，已自动回滚。\n错误：{}".format(result[:300]))
            await self.api.post_private_msg(
                user_id=int(user_qq),
                text="😞 开发过程遇到问题，代码已回滚，请稍后重新提交需求。")

    # ── 部署上线 ─────────────────────────────────
    async def _deploy(self, req: DevRequest, user_qq: str):
        req.touch()
        await asyncio.get_event_loop().run_in_executor(
            None, _git_commit_push, req.summary[:50])
        await asyncio.get_event_loop().run_in_executor(None, _restart_qiubot)
        async with self._lock:
            self._requests.pop(user_qq, None)
        await self.api.post_private_msg(
            user_id=int(ADMIN_QQ),
            text="✅ 已上线并重启 QiuBot，代码已推送到 GitHub。")
        await self.api.post_private_msg(
            user_id=int(user_qq),
            text="🚀 功能已上线！QiuBot 已重启，去群里试试吧～")
        if req.group_id:
            first_line = req.summary.splitlines()[0] if req.summary else "新功能"
            await self.api.post_group_msg(
                group_id=int(req.group_id),
                text="📢 新功能上线：{}\n（由 QQ {} 提需求）".format(first_line, user_qq))

    # ── 取消部署回滚 ────────────────────────────
    async def _deploy_cancel(self, req: DevRequest, user_qq: str):
        await asyncio.get_event_loop().run_in_executor(
            None, _git_rollback, req.git_snapshot)
        async with self._lock:
            self._requests.pop(user_qq, None)
        await self.api.post_private_msg(
            user_id=int(ADMIN_QQ), text="✅ 已取消，代码已回滚。")
        await self.api.post_private_msg(
            user_id=int(user_qq), text="需求已取消，代码已回滚。")

    # ── AI 需求分析 ──────────────────────────────
    async def _analyst(self, req: DevRequest) -> str:
        try:
            return await _call_claude(req.history, ANALYST_SYSTEM)
        except Exception as e:
            return "[AI 调用失败: {}]".format(e)


# ── 模块级工具函数（同步，在 executor 里运行）──────────

async def _call_claude(messages: list[dict], system: str) -> str:
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
    hermes_bin = Path.home() / ".hermes" / "bin" / "hermes"
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
        "【需求沟通】\n"
        "机器人会私聊你，通过几轮对话\n"
        "把你的想法整理成清晰的需求文档。\n"
        "你可以选择选项，也可以自由描述。\n"
        "最后回复「确认」提交审批。\n"
        "\n"
        "【审批与开发】\n"
        "管理员审批通过后，AI 自动开发，\n"
        "完成后管理员确认上线，群里会播报。\n"
        "━━━━━━━━━━━━━━\n"
        "注意事项：\n"
        "· 每人同时只能有一个进行中的需求\n"
        "· 管理员有权拒绝或取消任意需求\n"
        "· 开发失败会自动回滚，不影响现有功能\n"
        "━━━━━━━━━━━━━━\n"
        "#dev help   查看本帮助"
    )
