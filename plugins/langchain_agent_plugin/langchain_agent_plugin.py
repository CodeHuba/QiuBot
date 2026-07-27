"""
LangChain Agent Plugin - LangChain 1.3+ 版本

使用新的 create_agent API
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from ncatbot.plugin_system import NcatBotPlugin, on_message
from ncatbot.core.event import BaseMessageEvent

from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .tools import create_tools
from .memory_manager import MemoryManager

# 加载环境变量
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# ===== 配置 =====
API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_HISTORY_LENGTH = 10

# CQ 码正则
CQ_AT_RE_TPL = r"\[CQ:at,qq={qq}\]"
CQ_ANY_RE = re.compile(r"\[CQ:[^\]]+\]")


class LangChainAgentPlugin(NcatBotPlugin):
    """LangChain Agent 插件 - 1.3+ 版本"""

    name = "LangChainAgentPlugin"
    version = "2.0.0"

    async def on_load(self):
        """插件加载时初始化"""
        if not API_KEY:
            print(f"[{self.name}] ⚠️ 未配置 ANTHROPIC_API_KEY，插件不会响应")
            return

        print(f"[{self.name}] 正在初始化...")

        try:
            # 1. 初始化 LLM
            self.llm = ChatAnthropic(
                model=MODEL,
                anthropic_api_key=API_KEY,
                base_url=BASE_URL,
                max_tokens=2048,
                temperature=0.7,
            )
            print(f"[{self.name}] ✓ LLM 初始化完成 (model={MODEL})")

            # 2. 初始化会话记忆管理器
            self.memory_manager = MemoryManager(max_history=MAX_HISTORY_LENGTH)
            print(f"[{self.name}] ✓ 会话记忆管理器初始化完成")

            # 3. 创建工具
            self.tools = create_tools()
            print(f"[{self.name}] ✓ 工具加载完成 ({len(self.tools)} 个)")

            # 4. 系统提示词
            self.system_prompt = SystemMessage(content="""你是丘bot，一个专注于 The Bazaar 游戏的 QQ 群助手。

你可以使用工具来帮助用户：
- query_player: 查询玩家战绩
- query_encyclopedia: 查询游戏百科（物品/技能）
- generate_stat_chart: 生成玩家走势图
- duckduckgo_search: 搜索网络信息
- calculator: 执行数学计算

回复规则：
- 简洁友好，避免长篇大论
- 不要用 markdown 格式（QQ 群不渲染）
- 如果需要查询信息，主动调用工具
- 如果工具返回错误，友好地告知用户
- 记住用户的对话历史，提供连贯的回复""")

            # 5. 创建 Agent（LangChain 1.3+ API）
            self.agent = create_agent(
                model=self.llm,
                tools=self.tools,
                system_prompt=self.system_prompt,
            )

            print(f"[{self.name}] ✓ Agent 创建完成")
            print(f"[{self.name}] ✅ 插件加载成功 v{self.version}")

            self.bot_qq = None

        except Exception as e:
            print(f"[{self.name}] ❌ 初始化失败: {e}")
            import traceback
            traceback.print_exc()

    @on_message
    async def handle(self, event: BaseMessageEvent):
        """主消息处理"""
        if not API_KEY or not hasattr(self, 'agent'):
            return

        # 获取 Bot QQ
        if self.bot_qq is None:
            self.bot_qq = str(getattr(event, "self_id", "") or "")

        raw = event.raw_message or ""

        # 判断触发条件
        is_private = getattr(event, "message_type", "") == "private"
        is_at_bot = False

        if not is_private and self.bot_qq:
            at_pat = re.compile(CQ_AT_RE_TPL.format(qq=self.bot_qq))
            is_at_bot = bool(at_pat.search(raw))

        if not (is_private or is_at_bot):
            return

        # 有图片或引用消息 → 让位给 chat_plugin 处理
        if "[CQ:image," in raw or "[CQ:reply," in raw:
            return

        # 清理 CQ 码
        text = CQ_ANY_RE.sub("", raw).strip()

        # 空消息、纯 @ 打招呼 → 让位给 chat_plugin
        if not text:
            return

        # 传统指令跳过
        if text.startswith("#bz") or text.startswith("/bz"):
            return

        print(f"[{self.name}] 收到消息: {text}")

        # 获取用户记忆
        user_id = str(getattr(event, "user_id", "unknown"))
        memory = self.memory_manager.get_memory(user_id)

        # 构建完整的消息历史
        messages = list(memory.messages) + [HumanMessage(content=text)]

        # 调用 Agent
        try:
            print(f"[{self.name}] 正在调用 Agent...")
            
            # LangChain 1.3+ 的 create_agent 返回 CompiledStateGraph
            # 调用方式：agent.invoke({"messages": [...]})
            response = await self.agent.ainvoke({"messages": messages})

            # 提取回复
            if "messages" in response:
                last_message = response["messages"][-1]
                reply = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                reply = str(response)

            if reply:
                # 保存到记忆
                memory.add_message(HumanMessage(content=text))
                memory.add_message(AIMessage(content=reply))

                # 修剪记忆
                self.memory_manager.trim_memory(user_id)

                # 回复
                await event.reply(reply)
                print(f"[{self.name}] 回复: {reply[:100]}...")

        except Exception as e:
            print(f"[{self.name}] 处理出错: {e}")
            import traceback
            traceback.print_exc()
            await event.reply(f"处理出错了: {e}")
