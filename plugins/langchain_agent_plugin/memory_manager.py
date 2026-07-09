"""
会话记忆管理器

管理每个用户的对话历史
"""
from typing import Dict
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage


class MemoryManager:
    """会话记忆管理器"""

    def __init__(self, max_history: int = 10):
        """
        初始化

        Args:
            max_history: 每个用户最多保留的历史轮数
        """
        self.max_history = max_history
        self.memories: Dict[str, ChatMessageHistory] = {}

    def get_memory(self, user_id: str) -> ChatMessageHistory:
        """
        获取或创建用户的会话记忆

        Args:
            user_id: 用户 ID

        Returns:
            ChatMessageHistory 实例
        """
        if user_id not in self.memories:
            self.memories[user_id] = ChatMessageHistory()

        return self.memories[user_id]

    def clear_memory(self, user_id: str):
        """
        清除用户的会话记忆

        Args:
            user_id: 用户 ID
        """
        if user_id in self.memories:
            self.memories[user_id].clear()
            print(f"[Memory] 已清除用户 {user_id} 的会话记忆")

    def trim_memory(self, user_id: str):
        """
        修剪用户的会话记忆（保留最近 N 轮）

        Args:
            user_id: 用户 ID
        """
        if user_id not in self.memories:
            return

        memory = self.memories[user_id]
        messages = memory.messages

        # 如果超过最大历史长度，删除最早的消息
        if len(messages) > self.max_history * 2:  # 每轮 2 条消息（user + ai）
            keep_count = self.max_history * 2
            # 创建新的 ChatMessageHistory 只保留最近的消息
            new_history = ChatMessageHistory()
            for msg in messages[-keep_count:]:
                new_history.add_message(msg)
            self.memories[user_id] = new_history
            print(f"[Memory] 已修剪用户 {user_id} 的会话记忆，保留最近 {self.max_history} 轮")

    def get_all_users(self) -> list:
        """
        获取所有有会话记忆的用户 ID

        Returns:
            用户 ID 列表
        """
        return list(self.memories.keys())

    def get_memory_stats(self) -> dict:
        """
        获取会话记忆统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_users": len(self.memories),
            "users": {}
        }

        for user_id, memory in self.memories.items():
            message_count = len(memory.messages)
            stats["users"][user_id] = {
                "message_count": message_count,
                "rounds": message_count // 2,
            }

        return stats

    def export_memory(self, user_id: str) -> list:
        """
        导出用户的会话记忆（用于调试或持久化）

        Args:
            user_id: 用户 ID

        Returns:
            消息列表
        """
        if user_id not in self.memories:
            return []

        memory = self.memories[user_id]
        messages = memory.messages

        return [
            {
                "type": msg.type,
                "content": msg.content,
            }
            for msg in messages
        ]

    def import_memory(self, user_id: str, messages: list):
        """
        导入用户的会话记忆（用于恢复）

        Args:
            user_id: 用户 ID
            messages: 消息列表
        """
        memory = self.get_memory(user_id)
        memory.clear()

        for msg in messages:
            if msg["type"] == "human":
                memory.add_message(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                memory.add_message(AIMessage(content=msg["content"]))

        print(f"[Memory] 已导入用户 {user_id} 的会话记忆 ({len(messages)} 条)")


# 测试
if __name__ == "__main__":
    # 创建管理器
    manager = MemoryManager(max_history=3)

    # 模拟对话
    user_id = "12345"
    memory = manager.get_memory(user_id)

    memory.add_message(HumanMessage(content="你好"))
    memory.add_message(AIMessage(content="你好！我是丘bot"))

    memory.add_message(HumanMessage(content="帮我查 qqr"))
    memory.add_message(AIMessage(content="qqr 当前钻石2..."))

    memory.add_message(HumanMessage(content="给我他的走势图"))
    memory.add_message(AIMessage(content="[图片]"))

    memory.add_message(HumanMessage(content="谢谢"))
    memory.add_message(AIMessage(content="不客气！"))

    # 查看统计
    stats = manager.get_memory_stats()
    print(f"统计信息: {stats}")

    # 修剪记忆
    manager.trim_memory(user_id)

    # 再次查看统计
    stats = manager.get_memory_stats()
    print(f"修剪后: {stats}")

    # 导出记忆
    exported = manager.export_memory(user_id)
    print(f"导出的记忆: {exported}")
