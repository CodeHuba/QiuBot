# 快速开始指南

## 第一步：安装依赖

确保你已经安装了 Python 3.8 或更高版本，然后安装 NcatBot：

```bash
pip install ncatbot -U -i https://mirrors.aliyun.com/pypi/simple/
```

## 第二步：配置 Bot

有两种方式配置 Bot：

### 方式一：交互式配置（推荐新手）

直接运行 `python main.py`，程序会提示你输入：
- Bot QQ 号
- Root 管理员 QQ 号

### 方式二：配置文件（推荐）

1. 复制 `config_example.py` 为 `config.py`：
```bash
cp config_example.py config.py
```

2. 编辑 `config.py`，填入你的配置信息

3. 修改 `main.py`，使用配置文件启动

## 第三步：运行 Bot

```bash
python main.py
```

## 第四步：扫码登录

1. 运行后，终端会显示二维码或二维码链接
2. 使用手机 QQ 扫码登录 Bot 账号
3. 登录成功后，Bot 开始运行

## 第五步：测试功能

向 Bot 发送消息 "你是谁"，Bot 会回复 "我是崭新出炉的丘bot~"

## 常见问题

### Q: 提示端口被占用怎么办？
A: NcatBot 默认使用 3001 和 6099 端口。如果被占用，可以在配置中修改端口号。

### Q: 扫码后提示登录失败？
A: 确保你的电脑上没有同时登录该 QQ 号。

### Q: Bot 没有回复消息？
A: 检查：
1. Bot 是否成功登录
2. 消息是否完全匹配 "你是谁"（注意空格）
3. 查看终端是否有错误信息

### Q: 如何停止 Bot？
A: 在终端按 `Ctrl+C` 停止运行。

## 下一步

- 查看 `plugins/qiu_plugin/qiu_plugin.py` 了解插件开发
- 阅读 [NcatBot 官方文档](https://docs.ncatbot.xyz/) 学习更多功能
- 在插件中添加更多自定义功能
