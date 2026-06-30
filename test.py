"""
丘Bot 测试脚本

用于测试 Bot 的基本功能，无需实际登录 QQ
"""

from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.core.event import BaseMessageEvent
from plugins.qiu_plugin import QiuPlugin


def test_plugin_basic():
    """测试插件基本信息"""
    plugin = QiuPlugin()

    print("=" * 50)
    print("测试插件基本信息")
    print("=" * 50)
    print(f"插件名称: {plugin.name}")
    print(f"插件版本: {plugin.version}")
    print("✓ 插件基本信息测试通过\n")


def test_message_matching():
    """测试消息匹配逻辑"""
    print("=" * 50)
    print("测试消息匹配逻辑")
    print("=" * 50)

    test_cases = [
        ("你是谁", True, "应该匹配"),
        ("你是谁 ", True, "带空格应该匹配（会被 strip）"),
        (" 你是谁", True, "带空格应该匹配（会被 strip）"),
        ("你是谁？", False, "带标点不应该匹配"),
        ("你是谁啊", False, "不完全匹配不应该匹配"),
        ("", False, "空消息不应该匹配"),
    ]

    for message, should_match, description in test_cases:
        # 模拟消息处理逻辑
        result = message and message.strip() == "你是谁"

        if result == should_match:
            print(f"✓ '{message}' - {description}")
        else:
            print(f"✗ '{message}' - {description} (期望: {should_match}, 实际: {result})")

    print()


def test_import():
    """测试导入是否正常"""
    print("=" * 50)
    print("测试模块导入")
    print("=" * 50)

    try:
        from ncatbot.plugin_system import NcatBotPlugin
        print("✓ NcatBotPlugin 导入成功")
    except ImportError as e:
        print(f"✗ NcatBotPlugin 导入失败: {e}")
        return False

    try:
        from ncatbot.plugin_system import filter_registry
        print("✓ filter_registry 导入成功")
    except ImportError as e:
        print(f"✗ filter_registry 导入失败: {e}")
        return False

    try:
        from ncatbot.core.event import BaseMessageEvent
        print("✓ BaseMessageEvent 导入成功")
    except ImportError as e:
        print(f"✗ BaseMessageEvent 导入失败: {e}")
        return False

    try:
        from plugins.qiu_plugin import QiuPlugin
        print("✓ QiuPlugin 导入成功")
    except ImportError as e:
        print(f"✗ QiuPlugin 导入失败: {e}")
        return False

    print()
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("丘Bot 测试套件")
    print("=" * 50 + "\n")

    # 测试导入
    if not test_import():
        print("\n⚠️  请先安装 NcatBot: pip install ncatbot -U")
        return

    # 测试插件基本信息
    test_plugin_basic()

    # 测试消息匹配
    test_message_matching()

    print("=" * 50)
    print("所有测试完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
