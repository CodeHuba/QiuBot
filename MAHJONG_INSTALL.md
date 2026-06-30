"""
麻将牌谱分析插件 - 简化版安装指南
"""

# 安装步骤

## 1. 安装依赖

```bash
cd /d/PJ/QiuBot
pip install selenium undetected-chromedriver openpyxl
```

## 2. 验证安装

检查所有文件是否已创建：

```bash
# 插件文件
plugins/qiu_plugin/mahjong/__init__.py
plugins/qiu_plugin/mahjong/mahjong_plugin.py
plugins/qiu_plugin/mahjong/task_manager.py
plugins/qiu_plugin/mahjong/mortal_analyzer.py
plugins/qiu_plugin/mahjong/models.py

# 配置文件
data/mahjong/config.json

# 数据目录
data/mahjong/excel/
```

## 3. 配置 Bot

在你的 bot 启动文件中注册插件。查看 `main.py` 或 `start.py`，添加：

```python
from plugins.qiu_plugin import MahjongPlugin

# 在创建 bot 实例后
bot.register_plugin(MahjongPlugin())
```

或者如果使用配置文件方式：

```yaml
# config.yaml
plugins:
  - plugins.qiu_plugin.QiuPlugin
  - plugins.qiu_plugin.MahjongPlugin  # 添加这一行
```

## 4. 启动 Bot

```bash
cd /d/PJ/QiuBot
python start.py
```

## 5. 测试命令

在 QQ 中发送：

```
/mahjong 18558711 10
```

应该收到任务创建确认消息。

## 常见问题

### Q: 提示 "ModuleNotFoundError: No module named 'selenium'"
A: 运行 `pip install selenium undetected-chromedriver openpyxl`

### Q: 提示 "Chrome binary not found"
A: 确保系统已安装 Chrome 浏览器

### Q: 任务一直没有响应
A: 检查 bot 日志，查看是否有错误信息

### Q: 如何修改配置
A: 编辑 `data/mahjong/config.json` 文件

## 配置说明

### 无头模式（headless）
- `true`: 后台运行，不显示浏览器窗口（推荐）
- `false`: 显示浏览器窗口，用于调试

### 频率限制
- `max_requests_per_user`: 每个用户在时间窗口内的最大请求数
- `window_hours`: 时间窗口（小时）

### 分析场数
- `default_count`: 默认分析场数（不指定时使用）
- `min_count`: 最小分析场数
- `max_count`: 最大分析场数

## 文件说明

### mahjong_plugin.py
主插件类，处理命令和通知用户

### task_manager.py
任务管理器，管理任务队列和执行

### mortal_analyzer.py
Mortal 分析器封装，执行实际的牌谱分析

### models.py
数据模型定义

## 下一步

1. 测试基本功能是否正常
2. 根据需要调整配置
3. 监控日志，确保稳定运行
4. 收集用户反馈，优化体验

## 技术支持

如有问题，请查看：
- Bot 日志输出
- `plugins/qiu_plugin/mahjong/README.md` 详细文档
- 原始 Mortal.py 脚本的实现
