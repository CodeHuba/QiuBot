# LangChain Agent Plugin

> 基于 LangChain 的智能 Agent 插件，完全替换原 agent_plugin

**版本**: 2.0.0  
**作者**: Claude & 用户协作

---

## 功能特性

✨ **会话记忆** - 多轮对话上下文理解  
🔍 **RAG 检索** - 从知识库检索相关信息  
📊 **LangGraph** - 可视化状态流程编排  
🛠️ **丰富工具** - 游戏查询 + 网络搜索 + 更多  
📈 **可观测性** - LangSmith 调试追踪（可选）

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements-langchain.txt
```

### 2. 配置环境变量

在 `.env` 文件中添加：

```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# LangSmith（可选）
LANGSMITH_API_KEY=lsv2_xxx
LANGSMITH_PROJECT=qiubot
```

### 3. 准备知识库

将游戏知识文档放入 `data/knowledge_base/` 目录：

```
data/knowledge_base/
├── game_intro.txt          # 游戏简介
├── faqs/                   # 常见问题
├── strategies/             # 攻略文档
├── items/                  # 物品信息
├── skills/                 # 技能信息
└── heroes/                 # 英雄信息
```

### 4. 启动 Bot

```bash
python main.py
```

插件会自动：
1. 加载知识库文档
2. 构建向量索引（首次较慢）
3. 初始化 LangGraph Agent

---

## 使用方式

### 基础查询

```
用户: @Bot 帮我查 qqr 的战绩
Bot: qqr 当前钻石2段位，总胜率58.3%，已玩234场比赛
```

### 知识库查询

```
用户: @Bot 新手推荐什么英雄？
Bot: 新手推荐 Vanessa（瓦妮莎）。她的被动能力简单易懂，容错率高...
```

### 多轮对话

```
用户: @Bot 帮我查 qqr
Bot: qqr 当前钻石2...

用户: @Bot 他的胜率怎么样？
Bot: qqr 的胜率是 58.3%，属于比较高的水平...
```

### 网络搜索

```
用户: @Bot 最新的 Meta 是什么？
Bot: [自动搜索网络] 根据最新信息，当前 Meta 主要是...
```

---

## 架构设计

### 核心流程

```
用户消息
  ↓
LangChain Agent Plugin
  ↓
LangGraph 状态图
  ├─ retrieve 节点（知识检索）
  └─ agent 节点（Agent 决策）
      ├─ query_player 工具
      ├─ query_encyclopedia 工具
      ├─ web_search 工具
      └─ calculator 工具
  ↓
回复用户
```

### 文件结构

```
plugins/langchain_agent_plugin/
├── __init__.py                    # 插件导出
├── langchain_agent_plugin.py      # 核心插件（250 行）
├── graph_builder.py               # LangGraph 构建器（180 行）
├── tools.py                       # 工具定义（180 行）
├── memory_manager.py              # 会话记忆管理（120 行）
├── knowledge_base.py              # 知识库管理（150 行）
└── README.md                      # 本文档
```

---

## 核心组件

### 1. LangGraph 状态图

定义 Agent 的执行流程：

```python
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_node)  # 知识检索
workflow.add_node("agent", agent_node)        # Agent 决策
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "agent")
workflow.add_edge("agent", END)
```

### 2. 会话记忆

每个用户维护独立的对话历史：

```python
memory_manager = MemoryManager(max_history=10)
memory = memory_manager.get_memory(user_id)
```

### 3. 向量知识库

使用 FAISS 进行高效检索：

```python
vectorstore = FAISS.load_local("data/faiss_index", embeddings)
docs = vectorstore.similarity_search(query, k=3)
```

### 4. 工具集成

复用 bazaar_plugin 数据层 + 新增工具：

- `query_player` - 查询玩家战绩
- `query_encyclopedia` - 查询游戏百科
- `web_search` - 网络搜索
- `calculator` - 计算器

---

## 配置说明

### 环境变量

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API 密钥 |
| `ANTHROPIC_MODEL` | ❌ | 模型名称（默认 claude-sonnet-4-20250514） |
| `LANGSMITH_API_KEY` | ❌ | LangSmith 追踪密钥（可选） |
| `LANGSMITH_PROJECT` | ❌ | LangSmith 项目名（默认 qiubot） |

### 插件配置

在 `langchain_agent_plugin.py` 中：

```python
MAX_HISTORY_LENGTH = 10  # 最多保留 10 轮对话
```

在 `graph_builder.py` 中：

```python
max_iterations=5  # Agent 最多迭代 5 次
```

---

## 性能对比

| 指标 | 原生 API | LangChain |
|------|---------|-----------|
| 响应时间 | ~2s | ~3-4s |
| 功能 | 基础工具调用 | 工具+RAG+记忆 |
| 代码量 | 450 行 | 880 行（模块化） |
| 可扩展性 | 中 | 高 |
| 调试难度 | 低 | 中（有 LangSmith） |

---

## 故障排查

### 问题 1: 插件加载失败

**症状**: 启动时报错 `ImportError`

**解决**:
```bash
pip install -r requirements-langchain.txt
```

### 问题 2: 知识库检索失败

**症状**: 回复中没有使用知识库内容

**解决**:
1. 检查 `data/knowledge_base/` 是否有文档
2. 删除 `data/faiss_index/` 重新构建索引
3. 查看日志中的 `[KB]` 相关信息

### 问题 3: 会话记忆不工作

**症状**: 无法理解上下文

**解决**:
1. 检查 `memory_manager` 是否正确初始化
2. 查看日志确认记忆是否被保存
3. 测试：连续发送两条消息，第二条引用第一条

### 问题 4: 响应缓慢

**症状**: 回复时间 >10s

**可能原因**:
- 首次加载 Embedding 模型较慢
- 向量检索文档过多
- Claude API 网络延迟

**优化**:
- 使用缓存的向量索引
- 减少检索文档数量（k=3 → k=2）
- 使用 Claude API 代理

---

## 调试技巧

### 1. 启用 LangSmith

在 `.env` 中配置：

```bash
LANGSMITH_API_KEY=lsv2_xxx
LANGSMITH_PROJECT=qiubot
```

访问 [LangSmith](https://smith.langchain.com/) 查看详细追踪。

### 2. 查看日志

观察关键日志：

```bash
[LangChainAgentPlugin] ✓ 插件加载完成
[KB] ✓ 向量索引构建完成
[LangGraph] 检索到 3 个相关文档
[LangGraph] Agent 回复: ...
```

### 3. 测试知识库

```bash
cd plugins/langchain_agent_plugin
python knowledge_base.py
```

### 4. 测试工具

```bash
cd plugins/langchain_agent_plugin
python tools.py
```

---

## 扩展开发

### 添加新工具

在 `tools.py` 中：

```python
def my_tool_func(input: str) -> str:
    # 工具逻辑
    return "result"

my_tool = Tool(
    name="my_tool",
    description="工具描述",
    func=my_tool_func
)

tools.append(my_tool)
```

### 添加知识库内容

1. 在 `data/knowledge_base/` 下创建 `.txt` 或 `.md` 文件
2. 删除 `data/faiss_index/` 目录
3. 重启 Bot，自动重建索引

### 自定义 LangGraph 流程

在 `graph_builder.py` 中修改状态图：

```python
# 添加新节点
def custom_node(state: AgentState):
    # 节点逻辑
    return {...}

workflow.add_node("custom", custom_node)
workflow.add_edge("retrieve", "custom")
workflow.add_edge("custom", "agent")
```

---

## 最佳实践

1. **知识库维护** - 定期更新游戏知识，保持最新
2. **记忆管理** - 设置合理的历史长度（10 轮足够）
3. **成本控制** - 监控 Claude API 使用量
4. **性能优化** - 缓存常见查询结果
5. **错误处理** - 完善异常捕获和用户提示

---

## 相关文档

- [LangChain 接入方案](../../docs/langchain_integration_plan.md)
- [QiuBot 系统架构](../../docs/agent_design.md)
- [LangChain 官方文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)

---

## 更新日志

### v2.0.0 (2026-07-07)
- ✨ 完全替换原 agent_plugin
- ✨ 新增会话记忆功能
- ✨ 新增 RAG 知识库检索
- ✨ 集成 LangGraph 状态编排
- ✨ 新增网络搜索工具
- 📝 完善文档和示例

---

**需要帮助？** 查看 [故障排查](#故障排查) 或在 GitHub 提 Issue
