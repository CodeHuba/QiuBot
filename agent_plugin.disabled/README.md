# QiuBot Agent Plugin

## 功能简介

将 QiuBot 升级为智能 Agent，支持**自然语言交互**，无需记忆指令格式。

**核心特性：**
- 🤖 基于 Claude Tool Use API，AI 自主决策调用哪个工具
- 💬 自然语言触发，@Bot 直接问问题即可
- 🔧 无缝集成现有 bazaar_plugin 功能
- 🔄 与传统 `#bz` 指令共存，互不干扰

---

## 工作原理

```
用户: @Bot 帮我查 Vanessa 的胜率
  ↓
Claude 分析: 需要查询玩家信息
  ↓
调用工具: query_player(username="Vanessa")
  ↓
bazaar_client 返回数据
  ↓
Claude 整合结果: "Vanessa 当前段位钻石，总胜率 58.3%..."
  ↓
回复用户
```

**关键区别：**
- 传统模式：用户必须记住 `#bz me Vanessa`
- Agent 模式：用户直接说 "帮我查 Vanessa"，AI 自己理解并调用工具

---

## 触发方式

### 群聊
- **Agent 模式**：`@Bot` + 自然语言
  - ✅ `@丘bot 帮我查 Vanessa 的战绩`
  - ✅ `@丘bot Lugnut 是什么物品`
  - ✅ `@丘bot 给我看看 CodeHub 的走势图`

- **传统模式**：`#bz` 指令（原插件处理）
  - ✅ `#bz me Vanessa`
  - ✅ `#bz item Lugnut`

### 私聊
- **Agent 模式**：直接发送自然语言
  - ✅ `帮我查 Vanessa 的战绩`
  - ✅ `Lugnut 是什么`

---

## 可用工具

Agent 可以自动调用以下 3 个工具：

### 1. `query_player` - 查询玩家信息
**触发示例：**
- "帮我查 CodeHub 的战绩"
- "Vanessa 现在什么段位"
- "xxx 的胜率是多少"

**参数：**
- `username`: 玩家名（必填）
- `query_type`: `info`（基本信息）或 `stat`（详细统计）

---

### 2. `query_encyclopedia` - 查询游戏百科
**触发示例：**
- "Lugnut 是什么物品"
- "帮我查技能 Banana"
- "Jolly 是哪个商人"

**参数：**
- `type`: `item`（物品）、`skill`（技能）、`merchant`（商人）
- `name`: 名称（支持中英文模糊匹配）

---

### 3. `generate_stat_chart` - 生成走势图
**触发示例：**
- "给我生成 CodeHub 的走势图"
- "帮我看看 xxx 的段位变化"

**参数：**
- `username`: 玩家名（必填）

---

## 安装与配置

### 1. 环境要求
- Python 3.10+
- 已安装 `httpx`（用于调用 Claude API）

```bash
pip install httpx
```

### 2. 配置 API 密钥

在 `/mnt/d/PJ/QiuBot/.env` 中添加：

```bash
# Claude API 配置（Agent 必需）
ANTHROPIC_API_KEY=sk-ant-...你的密钥
ANTHROPIC_BASE_URL=https://api.anthropic.com  # 或自定义代理
ANTHROPIC_MODEL=claude-sonnet-4-6
```

### 3. 启动 Bot

```bash
cd /mnt/d/PJ/QiuBot
python main.py
```

插件会自动加载，看到以下日志表示成功：

```
[AgentPlugin] 已加载 v1.0.0 (Agent 模式)
[AgentPlugin] Bazaar 数据就绪: items=1146, skills=498
```

---

## 测试用例

### 在群里测试（需要 @Bot）

```
你: @丘bot 帮我查 Vanessa 的战绩
Bot: Vanessa 当前段位钻石 2，总胜率 58.3%，最近 10 场 7 胜 3 负

你: @丘bot Lugnut 是什么
Bot: Lugnut（螺帽）
🟨 黄金 | 中型 | 通用
💰 售价 3 金币
🔧 效果：相邻物品 +2 伤害
标签：武器, 工具

你: @丘bot 这是什么
Bot: 不好意思，能具体说一下你想查什么吗？可以问我游戏物品、玩家战绩、走势图等~
```

### 私聊测试（直接发消息）

```
你: 帮我查 CodeHub 的战绩
Bot: （调用 query_player 返回结果）

你: #bz me CodeHub
Bot: （bazaar_plugin 处理，格式不变）
```

---

## 技术细节

### Agent 循环流程

```python
while iteration < MAX_ITERATIONS:
    # 1. 发送消息给 Claude
    response = call_claude_api(messages, tools)
    
    # 2. 判断停止原因
    if stop_reason == "end_turn":
        return response.text  # 最终回复
    
    if stop_reason == "tool_use":
        # 3. 执行工具
        results = execute_tools(tool_blocks)
        
        # 4. 把结果返回给 Claude
        messages.append(tool_results)
        continue  # 继续循环
```

### 与原插件的共存逻辑

```python
# agent_plugin.py
if text.startswith("#bz") or text.startswith("/bz"):
    return  # 交给 bazaar_plugin 处理

# 否则进入 Agent 流程
```

---

## 常见问题

### Q1: Agent 不响应？
**检查：**
1. 是否 @Bot（群聊必需）
2. `.env` 里 `ANTHROPIC_API_KEY` 是否配置
3. 查看日志有无报错

### Q2: 提示"Agent 未配置"？
**解决：**
```bash
# 确认 .env 文件存在且有以下配置
ANTHROPIC_API_KEY=sk-ant-...
```

### Q3: 调用失败"503 Service Unavailable"？
**原因：** 代理端没有可用的 claude-sonnet-4-6 渠道

**解决：**
- 使用官方 API：`ANTHROPIC_BASE_URL=https://api.anthropic.com`
- 或切换模型：`ANTHROPIC_MODEL=claude-sonnet-3-5-20241022`

### Q4: 能否同时用传统指令和 Agent？
**可以！**
- 传统指令：`#bz me Vanessa`（精确、快速）
- Agent 模式：`@Bot 帮我查 Vanessa`（自然、灵活）

两种方式互不干扰。

---

## 性能与费用

### 单次查询成本
- 输入 Token：~300（系统提示 + 工具定义 + 用户消息）
- 输出 Token：~100（工具调用 + 最终回复）
- **总成本**：约 $0.002/次（claude-sonnet-4 价格）

### 优化建议
- 系统提示已压缩至最简
- 工具定义只包含必要字段
- 单次对话无历史上下文（节省 Token）

---

## 下一步扩展

### 1. 添加记忆功能
让 Agent 记住用户常查的玩家：
```python
# 在 _run_agent 中添加上下文
context = f"用户之前查过: {user_history}"
messages[0]["content"] = context + user_message
```

### 2. 多轮对话
维护会话历史（需要存储）：
```python
# 在插件中添加
self.conversations[user_id] = deque(maxlen=10)
```

### 3. 更多工具
- 对局历史详情
- 卡组推荐
- 实时排行榜
- Meta 分析

### 4. 接入其他 Agent 框架
当前是原生 API 实现，如果需要复杂流程可以迁移到：
- LangChain（更多抽象层）
- AutoGen（多 Agent 协作）

---

## 文件结构

```
plugins/agent_plugin/
├── __init__.py           # 插件注册
├── agent_plugin.py       # 主逻辑（447 行）
└── README.md            # 本文档
```

---

## 开源协议

与 QiuBot 主项目保持一致

---

## 作者

基于 Claude Tool Use API 实现，由 Hermes Agent 协助开发
