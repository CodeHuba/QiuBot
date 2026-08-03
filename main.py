from ncatbot.core import BotClient

# 创建 Bot 客户端
bot = BotClient()

# 以前台模式运行（插件模式）
# 连接到 localhost:3002（通过 SSH 隧道连接到本地 SnowLuma）
bot.run_frontend(
    ws_uri="ws://localhost:3002",
    ws_token="YOUR_WS_TOKEN",
    remote_mode=True
)
