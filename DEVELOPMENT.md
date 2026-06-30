"""
丘Bot 插件开发指南

本文档介绍如何在丘Bot中开发新功能
"""

# ============================================
# 示例1：添加更多关键词回复
# ============================================

from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import filter_registry
from ncatbot.core.event import BaseMessageEvent


class QiuPlugin(NcatBotPlugin):
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        print(f"[{self.name}] 插件已加载")

    @filter_registry.on_message
    async def handle_messages(self, event: BaseMessageEvent):
        """处理所有消息"""
        message = event.raw_message

        if not message:
            return

        message = message.strip()

        # 多个关键词回复
        if message == "你是谁":
            await event.reply("我是崭新出炉的丘bot~")
        elif message == "你好":
            await event.reply("你好呀！很高兴见到你~")
        elif message == "再见":
            await event.reply("再见！期待下次相遇~")


# ============================================
# 示例2：使用命令系统
# ============================================

from ncatbot.plugin_system import command_registry

class QiuPlugin(NcatBotPlugin):
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        print(f"[{self.name}] 插件已加载")

    # 命令：/help
    @command_registry.command("help")
    async def help_command(self, event: BaseMessageEvent):
        help_text = """
丘Bot 帮助菜单：
/help - 显示此帮助
/about - 关于丘Bot
/time - 显示当前时间
        """
        await event.reply(help_text.strip())

    # 命令：/about
    @command_registry.command("about")
    async def about_command(self, event: BaseMessageEvent):
        await event.reply("我是崭新出炉的丘bot~\n版本：1.0.0")

    # 命令：/time
    @command_registry.command("time")
    async def time_command(self, event: BaseMessageEvent):
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await event.reply(f"当前时间：{now}")


# ============================================
# 示例3：区分群聊和私聊
# ============================================

from ncatbot.plugin_system import group_filter, private_filter

class QiuPlugin(NcatBotPlugin):
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        print(f"[{self.name}] 插件已加载")

    # 只在群聊中响应
    @group_filter
    @filter_registry.on_message
    async def handle_group_message(self, event: BaseMessageEvent):
        if event.raw_message == "你是谁":
            await event.reply("我是崭新出炉的丘bot~", at=True)  # at=True 会@发送者

    # 只在私聊中响应
    @private_filter
    @filter_registry.on_message
    async def handle_private_message(self, event: BaseMessageEvent):
        if event.raw_message == "你是谁":
            await event.reply("我是崭新出炉的丘bot~\n这是私聊消息哦~")


# ============================================
# 示例4：带参数的命令
# ============================================

class QiuPlugin(NcatBotPlugin):
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        print(f"[{self.name}] 插件已加载")

    # 命令：/echo <消息>
    @command_registry.command("echo")
    async def echo_command(self, event: BaseMessageEvent, message: str):
        """复读命令"""
        await event.reply(f"你说：{message}")

    # 命令：/add <数字1> <数字2>
    @command_registry.command("add")
    async def add_command(self, event: BaseMessageEvent, num1: int, num2: int):
        """加法计算"""
        result = num1 + num2
        await event.reply(f"{num1} + {num2} = {result}")


# ============================================
# 示例5：发送图片
# ============================================

class QiuPlugin(NcatBotPlugin):
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        print(f"[{self.name}] 插件已加载")

    @command_registry.command("pic")
    async def send_picture(self, event: BaseMessageEvent):
        """发送图片"""
        # 方式1：发送本地图片
        await event.reply(image="./images/avatar.png")

        # 方式2：发送网络图片
        await event.reply(image="https://example.com/image.jpg")

        # 方式3：同时发送文字和图片
        await event.reply(text="这是一张图片", image="./images/avatar.png")


# ============================================
# 示例6：定时任务
# ============================================

from ncatbot.plugin_system import schedule_registry

class QiuPlugin(NcatBotPlugin):
    name = "QiuPlugin"
    version = "1.0.0"

    async def on_load(self):
        print(f"[{self.name}] 插件已加载")
        # 注册定时任务
        await self.setup_schedule()

    async def setup_schedule(self):
        """设置定时任务"""
        # 每天早上8点发送消息
        @schedule_registry.cron("0 8 * * *")
        async def morning_greeting():
            # 向指定群发送消息
            await self.bot.api.send_group_msg(
                group_id="群号",
                message="早上好！新的一天开始了~"
            )


# ============================================
# 更多功能
# ============================================

# 查看 NcatBot 官方文档了解更多：
# https://docs.ncatbot.xyz/

# 常用功能：
# - 权限管理（管理员、Root）
# - 数据库存储
# - 文件上传下载
# - 群管理（禁言、踢人）
# - 好友/群请求处理
# - 自定义过滤器
# - 插件配置项
