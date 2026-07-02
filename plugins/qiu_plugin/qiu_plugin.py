from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import on_message
from ncatbot.core.event import BaseMessageEvent


class QiuPlugin(NcatBotPlugin):
    """丘bot插件 - 实现自动回复功能"""
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        """插件加载时的初始化"""
        print(f"[{self.name}] 插件已加载，版本: {self.version}")

    @on_message
    async def handle_who_are_you(self, event: BaseMessageEvent):
        """处理'你是谁'消息"""
        # 打印调试信息
        print(f"[QiuPlugin] 收到消息: {event.raw_message}")

        # 获取消息内容
        message = event.raw_message

        # 检查消息是否为"你是谁"
        if message and message.strip() == "你是谁":
            print(f"[QiuPlugin] 匹配成功，准备回复")
            await event.reply("我是崭新出炉的丘bot~")

    @on_message
    async def handle_ping(self, event: BaseMessageEvent):
        """处理 /ping 指令，群聊中回复 pong"""
        message = event.raw_message
        if not message:
            return
        # 仅响应群聊消息
        if getattr(event, "message_type", None) != "group":
            return
        if message.strip() == "/ping":
            await event.reply("pong")
