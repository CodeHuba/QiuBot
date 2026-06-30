"""
丘Bot 配置示例文件

将此文件重命名为 config.py 并填入你的配置信息
"""

# Bot 配置
BOT_CONFIG = {
    # Bot 的 QQ 号
    "bt_uin": "你的Bot QQ号",

    # Root 管理员 QQ 号（拥有最高权限）
    "root": "你的管理员QQ号",

    # 可选：NapCat 配置
    # "napcat_port": 3001,  # NapCat HTTP 端口
    # "napcat_ws_port": 3001,  # NapCat WebSocket 端口
}

# 插件配置
PLUGIN_CONFIG = {
    # 是否启用调试模式
    "debug": True,

    # 自定义回复消息（可选）
    "custom_reply": "我是崭新出炉的丘bot~",
}
