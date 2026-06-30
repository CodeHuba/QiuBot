"""
丘Bot 使用增强版插件的主程序

使用增强版插件，包含更多功能
"""

from ncatbot.core import BotClient

# 创建 Bot 客户端
bot = BotClient()

print("=" * 50)
print("欢迎使用丘Bot（增强版）！")
print("=" * 50)
print("\n功能列表：")
print("  📝 基础回复：你是谁、你好、再见")
print("  🤖 命令系统：/help、/about、/time、/echo")
print("  👥 群聊功能：/groupinfo")
print("  👤 私聊功能：/userinfo")
print("\n正在启动 Bot...")
print("请使用手机 QQ 扫码登录\n")

# 以前台模式运行（插件模式）
# 运行后会自动加载 plugins 目录下的所有插件
bot.run_frontend()
