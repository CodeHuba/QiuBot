"""
LangGraph 构建器

构建包含 RAG 检索和 Agent 决策的状态图
"""
from typing import TypedDict, Annotated, Sequence
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


class AgentState(TypedDict):
    """Agent 状态定义"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_id: str
    query: str
    retrieved_docs: list
    tool_results: list
    final_answer: str


def build_agent_graph(llm, tools, vectorstore):
    """
    构建 LangGraph Agent

    流程：
    1. retrieve - 从知识库检索相关文档
    2. agent - Agent 决策并调用工具
    3. END - 结束
    """

    # ===== 系统提示词 =====
    SYSTEM_PROMPT = """你是丘bot，一个专注于 The Bazaar 游戏的 QQ 群助手。

你可以：
1. 查询玩家战绩（使用 query_player 工具）
2. 查询游戏百科（使用 query_encyclopedia 工具）
3. 搜索最新信息（使用 web_search 工具）
4. 执行计算（使用 calculator 工具）

知识库上下文：
{context}

回复规则：
- 简洁友好，避免长篇大论
- 不要用 markdown 格式（QQ 群不渲染）
- 优先使用知识库中的信息
- 如果知识库中没有，再考虑使用搜索工具
- 回复不超过 500 字
- 如果用户问题和游戏无关，礼貌回应即可
"""

    # ===== 创建 Prompt 模板 =====
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # ===== 创建 Agent =====
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
    )

    # ===== 定义节点 =====

    def retrieve_node(state: AgentState) -> dict:
        """检索节点：从知识库检索相关文档"""
        try:
            query = state["query"]
            print(f"[LangGraph] 检索知识库: {query}")

            if vectorstore is None:
                print("[LangGraph] 知识库未初始化，跳过检索")
                return {"retrieved_docs": []}

            # 向量检索（取 Top 3）
            docs = vectorstore.similarity_search(query, k=3)

            print(f"[LangGraph] 检索到 {len(docs)} 个相关文档")

            return {"retrieved_docs": docs}

        except Exception as e:
            print(f"[LangGraph] 检索失败: {e}")
            return {"retrieved_docs": []}

    def agent_node(state: AgentState) -> dict:
        """Agent 节点：决策并调用工具"""
        try:
            query = state["query"]
            retrieved_docs = state.get("retrieved_docs", [])
            messages = state.get("messages", [])

            print(f"[LangGraph] Agent 处理: {query}")

            # 构建上下文
            context = "\n\n".join([
                f"[文档 {i+1}]\n{doc.page_content}"
                for i, doc in enumerate(retrieved_docs)
            ]) if retrieved_docs else "暂无相关知识库信息"

            # 调用 Agent
            response = agent_executor.invoke({
                "input": query,
                "context": context,
                "chat_history": messages,
            })

            final_answer = response.get("output", "抱歉，我无法处理你的请求。")

            print(f"[LangGraph] Agent 回复: {final_answer[:50]}...")

            return {"final_answer": final_answer}

        except Exception as e:
            print(f"[LangGraph] Agent 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return {"final_answer": f"抱歉，处理时出现错误: {str(e)}"}

    # ===== 构建状态图 =====

    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("agent", agent_node)

    # 定义流程
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "agent")
    workflow.add_edge("agent", END)

    # 编译
    app = workflow.compile()

    print("[LangGraph] 状态图构建完成")

    return app


# ===== 可视化（可选） =====

def visualize_graph(app, output_path="langgraph_flow.png"):
    """
    可视化 LangGraph 流程图

    需要安装: pip install pygraphviz
    """
    try:
        from langgraph.graph import Graph

        # 生成 Mermaid 图
        mermaid_code = app.get_graph().draw_mermaid()

        print("LangGraph Mermaid 图:")
        print(mermaid_code)

        # 也可以生成 PNG（需要 pygraphviz）
        # app.get_graph().draw_png(output_path)
        # print(f"流程图已保存到: {output_path}")

    except Exception as e:
        print(f"可视化失败: {e}")


# 测试
if __name__ == "__main__":
    from langchain_anthropic import ChatAnthropic
    import os

    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    # 简单测试（无工具、无向量库）
    app = build_agent_graph(llm, [], None)

    print("\n✓ LangGraph 构建成功")

    # 可视化
    visualize_graph(app)
