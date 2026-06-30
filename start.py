#!/usr/bin/env python3
"""
丘Bot 快速启动脚本

自动检查环境并启动 Bot
"""

import sys
import subprocess
import os


def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 版本过低！")
        print(f"当前版本: {version.major}.{version.minor}.{version.micro}")
        print("需要版本: Python 3.8 或更高")
        print("\n请访问 https://www.python.org/downloads/ 下载最新版本")
        return False
    print(f"✓ Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True


def check_ncatbot_installed():
    """检查 NcatBot 是否已安装"""
    try:
        import ncatbot
        print(f"✓ NcatBot 已安装")
        return True
    except ImportError:
        print("❌ NcatBot 未安装")
        return False


def install_ncatbot():
    """安装 NcatBot"""
    print("\n正在安装 NcatBot...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "ncatbot", "-U",
            "-i", "https://mirrors.aliyun.com/pypi/simple/"
        ])
        print("✓ NcatBot 安装成功")
        return True
    except subprocess.CalledProcessError:
        print("❌ NcatBot 安装失败")
        print("\n请手动安装:")
        print("pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/")
        return False


def check_plugins():
    """检查插件目录"""
    if not os.path.exists("plugins/qiu_plugin"):
        print("❌ 插件目录不存在")
        return False
    if not os.path.exists("plugins/qiu_plugin/qiu_plugin.py"):
        print("❌ 插件文件不存在")
        return False
    print("✓ 插件文件存在")
    return True


def select_mode():
    """选择运行模式"""
    print("\n" + "=" * 50)
    print("请选择运行模式：")
    print("=" * 50)
    print("1. 基础版（简单回复功能）")
    print("2. 增强版（包含命令系统等更多功能）")
    print("3. 使用配置文件启动")
    print("=" * 50)

    while True:
        choice = input("\n请输入选项 (1/2/3): ").strip()
        if choice in ["1", "2", "3"]:
            return choice
        print("无效选项，请重新输入")


def run_bot(mode):
    """运行 Bot"""
    print("\n" + "=" * 50)
    print("正在启动丘Bot...")
    print("=" * 50)

    if mode == "1":
        script = "main.py"
    elif mode == "2":
        script = "main_enhanced.py"
    else:
        script = "main_with_config.py"

    if not os.path.exists(script):
        print(f"❌ 启动脚本 {script} 不存在")
        return False

    try:
        subprocess.run([sys.executable, script])
        return True
    except KeyboardInterrupt:
        print("\n\n✓ Bot 已停止")
        return True
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("丘Bot 快速启动脚本")
    print("=" * 50)
    print()

    # 检查 Python 版本
    if not check_python_version():
        sys.exit(1)

    # 检查 NcatBot 是否安装
    if not check_ncatbot_installed():
        install = input("\n是否现在安装 NcatBot? (y/n): ").strip().lower()
        if install == 'y':
            if not install_ncatbot():
                sys.exit(1)
        else:
            print("\n请先安装 NcatBot:")
            print("pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/")
            sys.exit(1)

    # 检查插件
    if not check_plugins():
        print("\n请确保项目结构完整")
        sys.exit(1)

    # 选择运行模式
    mode = select_mode()

    # 运行 Bot
    if not run_bot(mode):
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
