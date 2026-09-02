from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import on_message
from ncatbot.core.event import BaseMessageEvent
import re

# 语音转发配置
VOICE_FORWARD_FROM_QQ = "3810252006"   # 来源 QQ
VOICE_FORWARD_TO_GROUP = 1017811359    # 目标群

CQ_RECORD_RE = re.compile(r'\[CQ:record,[^\]]+\]')


class QiuPlugin(NcatBotPlugin):
    """丘bot插件 - 实现自动回复功能"""
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        """插件加载时的初始化"""
        print(f"[{self.name}] 插件已加载，版本: {self.version}")

    @on_message
    async def handle_voice_forward(self, event: BaseMessageEvent):
        """收到指定 QQ 的私聊语音，转发到目标群"""
        if getattr(event, "message_type", None) != "private":
            return
        if str(getattr(event, "user_id", "")) != VOICE_FORWARD_FROM_QQ:
            return
        raw = event.raw_message or ""
        if not CQ_RECORD_RE.search(raw):
            return
        m = re.search(r'\[CQ:record,file=([^\],]+)', raw)
        if not m:
            return
        file_val = m.group(1)
        try:
            await self.api.send_group_record(VOICE_FORWARD_TO_GROUP, file_val)
        except Exception as e:
            print(f"[QiuPlugin] 语音转发失败: {e}")

    @on_message
    async def handle_who_are_you(self, event: BaseMessageEvent):
        """处理'你是谁'消息"""
        message = event.raw_message
        if message and message.strip() == "你是谁":
            await event.reply("我是崭新出炉的丘bot~")

    @on_message
    async def handle_ping(self, event: BaseMessageEvent):
        """处理 /ping 指令，群聊中回复 pong"""
        message = event.raw_message
        if not message:
            return
        if getattr(event, "message_type", None) != "group":
            return
        if message.strip() == "/ping":
            await event.reply("pong")

