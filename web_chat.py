"""
LangChain Agent Web 界面

一个简单的 Flask Web 应用，支持在网页上与 Agent 对话
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import secrets

# 加载环境变量
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from plugins.langchain_agent_plugin.tools import create_tools
from plugins.langchain_agent_plugin.memory_manager import MemoryManager

# Flask 应用
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# 全局变量
agent = None
memory_manager = None
llm = None

# 配置
API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def init_agent():
    """初始化 Agent"""
    global agent, memory_manager, llm
    
    if not API_KEY:
        print("❌ 未配置 ANTHROPIC_API_KEY")
        return False
    
    try:
        print("正在初始化 LangChain Agent...")
        
        # 1. 初始化 LLM
        llm = ChatAnthropic(
            model=MODEL,
            anthropic_api_key=API_KEY,
            base_url=BASE_URL,
            max_tokens=2048,
            temperature=0.7,
        )
        print(f"✓ LLM 初始化完成 (model={MODEL})")
        
        # 2. 创建工具
        tools = create_tools()
        print(f"✓ 工具加载完成 ({len(tools)} 个)")
        
        # 3. 创建 Agent
        system_prompt = SystemMessage(content="""你是丘bot，一个专注于 The Bazaar 游戏的助手。

你可以使用工具来帮助用户：
- query_player: 查询玩家战绩
- query_encyclopedia: 查询游戏百科（物品/技能）
- generate_stat_chart: 生成玩家走势图
- calculator: 执行数学计算

回复规则：
- 简洁友好，避免长篇大论
- 可以使用 markdown 格式
- 如果需要查询信息，主动调用工具
- 如果工具返回错误，友好地告知用户""")
        
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
        )
        print("✓ Agent 创建完成")
        
        # 4. 初始化记忆管理器
        memory_manager = MemoryManager(max_history=20)
        print("✓ 会话记忆管理器初始化完成")
        
        print("✅ Agent 初始化成功！")
        return True
        
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


@app.route('/')
def index():
    """首页"""
    # 为每个用户分配唯一 session ID
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(8)
    
    return render_template('chat.html', model=MODEL)


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天 API"""
    if not agent:
        return jsonify({
            'error': 'Agent 未初始化',
            'reply': '抱歉，Agent 初始化失败，请检查配置。'
        }), 500
    
    data = request.json
    user_input = data.get('message', '').strip()
    
    if not user_input:
        return jsonify({'error': '消息不能为空'}), 400
    
    # 获取用户 ID
    user_id = session.get('user_id', 'default')
    
    try:
        # 获取用户记忆
        memory = memory_manager.get_memory(user_id)
        
        # 构建消息历史
        messages = list(memory.messages) + [HumanMessage(content=user_input)]
        
        # 调用 Agent（异步转同步）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(agent.ainvoke({"messages": messages}))
        loop.close()
        
        # 提取回复
        if "messages" in response:
            last_message = response["messages"][-1]
            reply = last_message.content if hasattr(last_message, 'content') else str(last_message)
        else:
            reply = str(response)
        
        # 保存到记忆
        memory.add_message(HumanMessage(content=user_input))
        memory.add_message(AIMessage(content=reply))
        memory_manager.trim_memory(user_id)
        
        return jsonify({
            'reply': reply,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        print(f"处理出错: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'error': str(e),
            'reply': f'处理出错了: {e}'
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """清除会话历史"""
    user_id = session.get('user_id', 'default')
    
    if memory_manager:
        memory_manager.clear_memory(user_id)
    
    return jsonify({'success': True, 'message': '会话历史已清除'})


@app.route('/api/stats')
def stats():
    """获取统计信息"""
    if not memory_manager:
        return jsonify({'error': 'Memory manager 未初始化'}), 500
    
    stats = memory_manager.get_memory_stats()
    return jsonify(stats)


@app.route('/charts/<path:filename>')
def serve_chart(filename):
    """提供图表文件访问"""
    from flask import send_from_directory
    charts_dir = PROJECT_ROOT / 'data' / 'charts'
    return send_from_directory(charts_dir, filename)


if __name__ == '__main__':
    # 初始化 Agent
    if init_agent():
        print("\n" + "=" * 60)
        print("🚀 Web 服务启动成功！")
        print("=" * 60)
        print(f"访问: http://localhost:5000")
        print(f"模型: {MODEL}")
        print("=" * 60 + "\n")
        
        # 启动 Flask
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        print("❌ Agent 初始化失败，无法启动 Web 服务")
