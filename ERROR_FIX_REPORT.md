# 错误修复报告

## 问题描述

```
[21:02:53.768] ERROR    ncatbot.plugin_system.builtin_plugin.unified_registry.plugin 'plugin.py:112' |
执行函数 handle_who_are_you 时发生错误: QiuPlugin.handle_who_are_you() missing 1 required positional argument: 'event'
```

## 问题原因

使用了错误的装饰器导入方式。原代码使用了 `@on_message` 装饰器，但正确的方式应该是使用 `@filter_registry.on_message`。

### 错误的代码

```python
from ncatbot.plugin_system import on_message

@on_message
async def handle_who_are_you(self, event: BaseMessageEvent):
    ...
```

### 正确的代码

```python
from ncatbot.plugin_system import filter_registry

@filter_registry.on_message
async def handle_who_are_you(self, event: BaseMessageEvent):
    ...
```

## 修复内容

### 1. 修复 `plugins/qiu_plugin/qiu_plugin.py`

**修改前：**
```python
from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import on_message
from ncatbot.core.event import BaseMessageEvent

class QiuPlugin(NcatBotPlugin):
    @on_message
    async def handle_who_are_you(self, event: BaseMessageEvent):
        ...
```

**修改后：**
```python
from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import filter_registry
from ncatbot.core.event import BaseMessageEvent

class QiuPlugin(NcatBotPlugin):
    @filter_registry.on_message
    async def handle_who_are_you(self, event: BaseMessageEvent):
        ...
```

### 2. 修复 `plugins/qiu_plugin/mahjong/mahjong_plugin.py`

**修改前：**
```python
from ncatbot.plugin_system import NcatBotPlugin, on_message
from ncatbot.core.event import BaseMessageEvent

class MahjongPlugin(NcatBotPlugin):
    @on_message
    async def handle_mahjong_command(self, event: BaseMessageEvent):
        ...
```

**修改后：**
```python
from ncatbot.plugin_system import NcatBotPlugin, filter_registry
from ncatbot.core.event import BaseMessageEvent

class MahjongPlugin(NcatBotPlugin):
    @filter_registry.on_message
    async def handle_mahjong_command(self, event: BaseMessageEvent):
        ...
```

## 参考示例

参考了 `plugins/qiu_plugin/qiu_plugin_enhanced.py` 中的正确用法：

```python
from ncatbot.plugin_system import filter_registry

@filter_registry.on_message
async def handle_who_are_you(self, event: BaseMessageEvent):
    ...
```

## 验证方法

重新启动 Bot 后，错误应该消失。可以通过以下方式测试：

1. **测试 QiuPlugin**：
   - 发送消息："你是谁"
   - 应该收到回复："我是崭新出炉的丘bot~"

2. **测试 MahjongPlugin**：
   - 发送命令：`/mahjong 18558711 10`
   - 应该收到任务创建确认消息

## 总结

- ✅ 修复了 `qiu_plugin.py` 的装饰器使用
- ✅ 修复了 `mahjong_plugin.py` 的装饰器使用
- ✅ 两个插件现在都使用正确的 `@filter_registry.on_message` 装饰器
- ✅ 错误 "missing 1 required positional argument: 'event'" 应该已解决

## 注意事项

在 NcatBot 框架中，有两种主要的装饰器使用方式：

1. **消息过滤器**：`@filter_registry.on_message` - 用于处理所有消息
2. **命令注册**：`@command_registry.command("命令名")` - 用于处理特定命令

对于麻将插件，由于需要匹配 `/mahjong` 命令，使用 `@filter_registry.on_message` 并在函数内部进行正则匹配是合适的。

如果想要更简洁的命令处理，也可以改用：
```python
@command_registry.command("mahjong")
async def handle_mahjong_command(self, event: BaseMessageEvent, player_id: str = "", count: str = ""):
    ...
```

但当前的实现方式也是可行的。
