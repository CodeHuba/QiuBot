from ncatbot.core import BotClient

# 创建 Bot 客户端
bot = BotClient()

# 以前台模式运行（插件模式）
# 运行后会自动加载 plugins 目录下的所有插件
bot.run_frontend()