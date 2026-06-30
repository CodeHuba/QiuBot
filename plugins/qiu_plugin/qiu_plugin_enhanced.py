"""
丘Bot 增强版插件

包含更多实用功能的版本
"""

from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import filter_registry, command_registry
from ncatbot.plugin_system import group_filter, private_filter
from ncatbot.core.event import BaseMessageEvent
from datetime import datetime


class QiuPluginEnhanced(NcatBotPlugin):
    """丘bot增强版插件"""
    name = "QiuPluginEnhanced"
    version = "1.1.0"

    async def on_load(self):
        """插件加载时的初始化"""
        print(f"[{self.name}] 插件已加载，版本: {self.version}")
        print(f"[{self.name}] 功能列表：")
        print("  - 自动回复'你是谁'")
        print("  - /help - 显示帮助")
        print("  - /about - 关于信息")
        print("  - /time - 当前时间")
        print("  - /echo <消息> - 复读")

    # ==================== 基础回复功能 ====================

    @filter_registry.on_message
    async def handle_who_are_you(self, event: BaseMessageEvent):
        """处理'你是谁'消息"""
        message = event.raw_message

        if not message:
            return

        message = message.strip()

        # 基础回复
        if message == "你是谁":
            await event.reply("我是崭新出炉的丘bot~")
        elif message == "你好" or message == "hi" or message == "hello":
            await event.reply("你好呀！很高兴见到你~ 😊")
        elif message == "再见" or message == "拜拜":
            await event.reply("再见！期待下次相遇~ 👋")

    # ==================== 命令系统 ====================

    @command_registry.command("help")
    async def help_command(self, event: BaseMessageEvent):
        """显示帮助信息"""
        help_text = """
🤖 丘Bot 帮助菜单

📝 基础命令：
/help - 显示此帮助
/about - 关于丘Bot
/time - 显示当前时间
/echo <消息> - 复读你的消息

💬 关键词回复：
你是谁 - 自我介绍
你好/hi/hello - 打招呼
再见/拜拜 - 告别

💡 提示：命令需要以 / 开头
        """
        await event.reply(help_text.strip())

    @command_registry.command("about")
    async def about_command(self, event: BaseMessageEvent):
        """关于信息"""
        about_text = f"""
🤖 关于丘Bot

名称：丘Bot
版本：{self.version}
简介：我是崭新出炉的丘bot~

基于 NcatBot 框架开发
项目地址：https://github.com/liyihao1110/ncatbot
        """
        await event.reply(about_text.strip())

    @command_registry.command("time")
    async def time_command(self, event: BaseMessageEvent):
        """显示当前时间"""
        now = datetime.now()
        time_text = f"""
⏰ 当前时间

日期：{now.strftime('%Y年%m月%d日')}
时间：{now.strftime('%H:%M:%S')}
星期：{['一', '二', '三', '四', '五', '六', '日'][now.weekday()]}
        """
        await event.reply(time_text.strip())

    @command_registry.command("echo")
    async def echo_command(self, event: BaseMessageEvent, message: str = ""):
        """复读命令"""
        if not message:
            await event.reply("请输入要复读的内容！\n用法：/echo <消息>")
        else:
            await event.reply(f"📢 {message}")

    # ==================== 群聊专属功能 ====================

    @group_filter
    @command_registry.command("groupinfo")
    async def group_info_command(self, event: BaseMessageEvent):
        """显示群信息（仅群聊可用）"""
        info_text = f"""
👥 群聊信息

群号：{event.group_id}
发送者：{event.user_id}
消息ID：{event.message_id}
        """
        await event.reply(info_text.strip())

    # ==================== 私聊专属功能 ====================

    @private_filter
    @command_registry.command("userinfo")
    async def user_info_command(self, event: BaseMessageEvent):
        """显示用户信息（仅私聊可用）"""
        info_text = f"""
👤 用户信息

QQ号：{event.user_id}
消息ID：{event.message_id}
        """
        await event.reply(info_text.strip())
