# 丘Bot - QiuBot

一个基于 NcatBot 开发的 QQ 机器人。

## 功能

- 当收到消息"你是谁"时，自动回复"我是崭新出炉的丘bot~"

## 环境要求

- Python >= 3.8
- NcatBot

## 安装

1. 安装 NcatBot：
```bash
pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/
```

2. 克隆或下载本项目

## 使用方法

1. 在项目根目录下运行：
```bash
python main.py
```

2. 首次运行时，会提示输入以下信息：
   - Bot QQ 号（bt_uin）
   - Root 管理员 QQ 号（拥有最高权限）

3. 使用手机 QQ 扫码登录 Bot 账号

4. 登录成功后，向 Bot 发送"你是谁"，即可收到回复"我是崭新出炉的丘bot~"

## 项目结构

```
QiuBot/
├── main.py                      # 主程序入口
├── plugins/                     # 插件目录
│   └── qiu_plugin/             # 丘bot插件
│       ├── __init__.py         # 插件导出
│       └── qiu_plugin.py       # 插件主逻辑
└── README.md                    # 项目说明
```

## 开发说明

### 插件开发

本项目使用 NcatBot 的插件系统开发。主要文件：

- `plugins/qiu_plugin/qiu_plugin.py`: 插件主逻辑
  - 使用 `@filter_registry.on_message` 装饰器监听所有消息
  - 检查消息内容是否为"你是谁"
  - 使用 `event.reply()` 方法回复消息

### 扩展功能

如需添加更多功能，可以在 `QiuPlugin` 类中添加更多方法：

```python
@filter_registry.on_message
async def another_handler(self, event: BaseMessageEvent):
    # 处理其他消息
    pass
```

## 注意事项

- 运行前请确保退出电脑上 Bot QQ 号的登录
- Bot 会占用本机 6099 和 3001 端口
- 如需修改配置，可参考 NcatBot 官方文档的配置项说明

## 相关链接

- [NcatBot 官方文档](https://docs.ncatbot.xyz/)
- [NcatBot GitHub](https://github.com/liyihao1110/ncatbot)