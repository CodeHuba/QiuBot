"""
丘Bot 工具函数模块

提供一些常用的工具函数
"""

from datetime import datetime
from typing import Optional
import re


def get_current_time_str(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前时间字符串

    Args:
        format: 时间格式，默认为 "%Y-%m-%d %H:%M:%S"

    Returns:
        格式化的时间字符串
    """
    return datetime.now().strftime(format)


def get_greeting_by_time() -> str:
    """
    根据当前时间返回问候语

    Returns:
        问候语字符串
    """
    hour = datetime.now().hour

    if 5 <= hour < 12:
        return "早上好"
    elif 12 <= hour < 14:
        return "中午好"
    elif 14 <= hour < 18:
        return "下午好"
    elif 18 <= hour < 22:
        return "晚上好"
    else:
        return "夜深了"


def extract_qq_number(text: str) -> Optional[str]:
    """
    从文本中提取 QQ 号

    Args:
        text: 输入文本

    Returns:
        QQ号字符串，如果没有找到则返回 None
    """
    pattern = r'\d{5,11}'
    match = re.search(pattern, text)
    return match.group() if match else None


def is_valid_qq_number(qq: str) -> bool:
    """
    验证 QQ 号是否有效

    Args:
        qq: QQ号字符串

    Returns:
        是否有效
    """
    return qq.isdigit() and 5 <= len(qq) <= 11


def format_message_list(items: list, title: str = "列表") -> str:
    """
    格式化消息列表

    Args:
        items: 列表项
        title: 列表标题

    Returns:
        格式化的字符串
    """
    if not items:
        return f"{title}：\n（空）"

    result = [f"{title}："]
    for i, item in enumerate(items, 1):
        result.append(f"{i}. {item}")

    return "\n".join(result)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 输入文本
        max_length: 最大长度
        suffix: 截断后的后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_command_args(message: str, command: str) -> list:
    """
    解析命令参数

    Args:
        message: 完整消息
        command: 命令名称

    Returns:
        参数列表
    """
    # 移除命令前缀
    if message.startswith(f"/{command}"):
        args_str = message[len(command) + 1:].strip()
        if args_str:
            return args_str.split()
    return []


def format_duration(seconds: int) -> str:
    """
    格式化时长

    Args:
        seconds: 秒数

    Returns:
        格式化的时长字符串
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}分{secs}秒"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分"


def is_at_message(message: str, bot_qq: str) -> bool:
    """
    检查消息是否@了机器人

    Args:
        message: 消息内容
        bot_qq: 机器人QQ号

    Returns:
        是否@了机器人
    """
    return f"[CQ:at,qq={bot_qq}]" in message


def remove_at_from_message(message: str) -> str:
    """
    从消息中移除@标记

    Args:
        message: 消息内容

    Returns:
        移除@后的消息
    """
    return re.sub(r'\[CQ:at,qq=\d+\]', '', message).strip()


class MessageBuilder:
    """消息构建器"""

    def __init__(self):
        self.parts = []

    def add_text(self, text: str) -> 'MessageBuilder':
        """添加文本"""
        self.parts.append(text)
        return self

    def add_line(self, text: str = "") -> 'MessageBuilder':
        """添加一行"""
        self.parts.append(text + "\n")
        return self

    def add_separator(self, char: str = "-", length: int = 20) -> 'MessageBuilder':
        """添加分隔符"""
        self.parts.append(char * length + "\n")
        return self

    def add_title(self, title: str) -> 'MessageBuilder':
        """添加标题"""
        self.parts.append(f"\n{'=' * 20}\n{title}\n{'=' * 20}\n")
        return self

    def build(self) -> str:
        """构建消息"""
        return "".join(self.parts)


# 使用示例
if __name__ == "__main__":
    # 测试工具函数
    print("当前时间:", get_current_time_str())
    print("问候语:", get_greeting_by_time())
    print("提取QQ号:", extract_qq_number("我的QQ是123456789"))
    print("验证QQ号:", is_valid_qq_number("123456789"))

    # 测试消息构建器
    builder = MessageBuilder()
    message = (builder
               .add_title("测试标题")
               .add_line("第一行内容")
               .add_line("第二行内容")
               .add_separator()
               .add_text("结束")
               .build())
    print(message)
