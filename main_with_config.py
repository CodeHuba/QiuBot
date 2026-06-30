"""
丘Bot 主程序（带配置文件支持版本）

使用方式：
1. 复制 config_example.py 为 config.py
2. 修改 config.py 中的配置
3. 运行 python main_with_config.py
"""

from ncatbot.core import BotClient
import os
import sys


def load_config():
    """加载配置文件"""
    try:
        # 尝试导入配置文件
        import config
        return config.BOT_CONFIG
    except ImportError:
        print("=" * 50)
        print("未找到配置文件 config.py")
        print("请复制 config_example.py 为 config.py 并填入配置信息")
        print("或者直接运行 main.py 使用交互式配置")
        print("=" * 50)
        sys.exit(1)


def main():
    """主函数"""
    print("=" * 50)
    print("欢迎使用丘Bot！")
    print("=" * 50)

    # 加载配置
    config = load_config()

    # 创建 Bot 客户端
    bot = BotClient()

    print(f"\nBot QQ号: {config.get('bt_uin')}")
    print(f"管理员QQ号: {config.get('root')}")
    print("\n正在启动 Bot...")
    print("请使用手机 QQ 扫码登录\n")

    # 以前台模式运行
    bot.run_frontend(
        bt_uin=config.get('bt_uin'),
        root=config.get('root')
    )


if __name__ == "__main__":
    main()
