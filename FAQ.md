# 常见问题解答 (FAQ)

## 安装相关

### Q1: 如何安装 NcatBot？

```bash
pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/
```

如果安装速度慢，可以使用国内镜像源。

### Q2: 提示 Python 版本不兼容怎么办？

NcatBot 需要 Python 3.8 或更高版本。请升级你的 Python：
- 访问 https://www.python.org/downloads/
- 下载并安装最新版本的 Python

### Q3: pip 命令不存在？

确保 Python 已正确安装并添加到系统 PATH。可以尝试：
```bash
python -m pip install ncatbot -U
```

## 运行相关

### Q4: 提示端口被占用怎么办？

NcatBot 默认使用 3001 和 6099 端口。如果被占用：

1. 检查是否有其他 NcatBot 实例在运行
2. 关闭占用端口的程序
3. 或者在配置中修改端口号

### Q5: 扫码后提示登录失败？

可能的原因：
1. 电脑上已经登录了该 QQ 号 - 请先退出登录
2. QQ 版本过旧 - 请更新到最新版本
3. 网络问题 - 检查网络连接

### Q6: Bot 启动后没有反应？

检查以下几点：
1. 是否成功扫码登录
2. 查看终端是否有错误信息
3. 确认插件是否正确加载（查看启动日志）

### Q7: 如何停止 Bot？

在终端按 `Ctrl+C` 即可停止运行。

## 功能相关

### Q8: Bot 没有回复消息？

检查：
1. 消息内容是否完全匹配（注意空格和标点）
2. Bot 是否在该群/好友列表中
3. 查看终端日志，确认是否收到消息
4. 检查插件是否正确加载

### Q9: 如何添加新的关键词回复？

编辑 `plugins/qiu_plugin/qiu_plugin.py`，在 `handle_who_are_you` 方法中添加：

```python
elif message == "新关键词":
    await event.reply("新回复内容")
```

### Q10: 如何让 Bot 只在特定群响应？

使用群组过滤器：

```python
@group_filter
async def handle_message(self, event: BaseMessageEvent):
    # 检查群号
    if event.group_id == "你的群号":
        await event.reply("只在特定群响应")
```

### Q11: 如何添加管理员权限？

使用管理员过滤器：

```python
from ncatbot.plugin_system import admin_filter

@admin_filter
@command_registry.command("admin")
async def admin_command(self, event: BaseMessageEvent):
    await event.reply("这是管理员命令")
```

### Q12: 如何发送图片？

```python
await event.reply(image="./path/to/image.png")
# 或者网络图片
await event.reply(image="https://example.com/image.jpg")
```

## 开发相关

### Q13: 如何调试插件？

1. 在代码中添加 print 语句查看变量值
2. 查看终端输出的日志信息
3. 使用 `test.py` 进行单元测试

### Q14: 如何保存数据？

使用项目提供的 `DataManager`：

```python
from plugins.qiu_plugin.data_manager import DataManager

dm = DataManager()
dm.save("key", {"data": "value"})
data = dm.load("key")
```

### Q15: 如何添加定时任务？

参考 `DEVELOPMENT.md` 中的定时任务示例。

### Q16: 插件修改后需要重启吗？

是的，修改插件代码后需要重启 Bot 才能生效。

## 错误处理

### Q17: 提示 "ModuleNotFoundError: No module named 'ncatbot'"

NcatBot 未安装或安装失败，请重新安装：
```bash
pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/
```

### Q18: 提示 "ImportError: cannot import name 'xxx'"

可能是 NcatBot 版本不兼容，请更新到最新版本：
```bash
pip install ncatbot -U --force-reinstall
```

### Q19: 运行时出现乱码？

确保：
1. Python 文件使用 UTF-8 编码保存
2. 终端支持 UTF-8 显示
3. Windows 用户可以在终端执行：`chcp 65001`

### Q20: 提示权限错误？

某些操作可能需要管理员权限：
- Windows: 以管理员身份运行终端
- Linux/Mac: 使用 `sudo` 命令

## 其他问题

### Q21: 如何更新 NcatBot？

```bash
pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/
```

### Q22: 如何查看 NcatBot 版本？

```bash
pip show ncatbot
```

### Q23: 在哪里可以获得帮助？

1. 查看 [NcatBot 官方文档](https://docs.ncatbot.xyz/)
2. 查看项目的 README.md 和其他文档
3. 在 GitHub 上提 Issue
4. 加入 NcatBot 交流群

### Q24: 如何贡献代码？

查看 `CONTRIBUTING.md` 了解贡献指南。

### Q25: 项目使用什么许可证？

本项目基于 NcatBot，遵循其许可证要求。具体请查看 NcatBot 的许可证说明。

---

## 还有其他问题？

如果以上内容没有解决你的问题：

1. 查看完整的 [NcatBot 文档](https://docs.ncatbot.xyz/)
2. 在 GitHub 上搜索相关 Issue
3. 创建新的 Issue 描述你的问题
4. 加入社区交流群寻求帮助

记得在提问时提供：
- 操作系统和版本
- Python 版本
- NcatBot 版本
- 完整的错误信息
- 复现步骤
