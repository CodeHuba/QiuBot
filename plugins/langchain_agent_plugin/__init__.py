"""
LangChain Agent Plugin for QiuBot

基于 LangChain 的智能 Agent，支持：
- 会话记忆（多轮对话）
- RAG 知识检索
- LangGraph 状态编排
- 丰富的工具生态
"""

from .langchain_agent_plugin import LangChainAgentPlugin

__all__ = ["LangChainAgentPlugin"]
