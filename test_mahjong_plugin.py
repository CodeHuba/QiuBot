"""
麻将牌谱分析插件测试脚本
"""

import asyncio
from plugins.qiu_plugin.mahjong.models import MahjongTask, DEFAULT_CONFIG
from plugins.qiu_plugin.mahjong.task_manager import MahjongTaskManager, RateLimiter


async def test_rate_limiter():
    """测试频率限制器"""
    print("\n=== 测试频率限制器 ===")
    limiter = RateLimiter(max_requests=3, window_hours=24)

    user_id = "test_user_123"

    # 测试前3次请求
    for i in range(4):
        allowed, reset_time = limiter.check_limit(user_id)
        if allowed:
            print(f"✅ 请求 {i+1}: 允许")
        else:
            print(f"❌ 请求 {i+1}: 被限制，重置时间: {reset_time}")


async def test_task_creation():
    """测试任务创建"""
    print("\n=== 测试任务创建 ===")

    # 模拟通知回调
    async def notify_callback(event_type, task, data):
        print(f"[通知] {event_type}: 任务 {task.task_id}, 进度 {task.progress:.0f}%")

    manager = MahjongTaskManager(DEFAULT_CONFIG, notify_callback)

    # 创建任务
    success, message, task = await manager.create_task(
        user_id="test_user_456",
        player_id="18558711",
        count=10
    )

    if success:
        print(f"✅ 任务创建成功: {task.task_id}")
        print(f"   玩家ID: {task.player_id}")
        print(f"   分析场数: {task.count}")
    else:
        print(f"❌ 任务创建失败: {message}")

    # 等待任务完成（或超时）
    if success:
        print("\n等待任务执行...")
        await asyncio.sleep(5)  # 等待5秒看看任务状态

        current = manager.get_current_task()
        if current:
            print(f"当前任务状态: {current.status}")
            print(f"当前进度: {current.progress:.0f}%")


async def test_config():
    """测试配置加载"""
    print("\n=== 测试配置加载 ===")
    from plugins.qiu_plugin.data_manager import DataManager

    dm = DataManager("data/mahjong")
    config = dm.load("config", default=DEFAULT_CONFIG)

    print(f"✅ 配置加载成功")
    print(f"   无头模式: {config['browser']['headless']}")
    print(f"   默认场数: {config['analysis']['default_count']}")
    print(f"   最大场数: {config['analysis']['max_count']}")
    print(f"   频率限制: {config['rate_limit']['max_requests_per_user']}次/{config['rate_limit']['window_hours']}小时")


async def main():
    """主测试函数"""
    print("=" * 50)
    print("麻将牌谱分析插件测试")
    print("=" * 50)

    try:
        # 测试配置
        await test_config()

        # 测试频率限制
        await test_rate_limiter()

        # 注意：实际的任务执行测试需要浏览器环境，这里只测试任务创建
        # await test_task_creation()

        print("\n" + "=" * 50)
        print("✅ 基础测试完成")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
