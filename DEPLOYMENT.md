# 部署指南

本文档介绍如何在不同环境下部署丘Bot。

## 本地开发环境

### Windows

1. 安装 Python 3.8+
2. 打开命令提示符或 PowerShell
3. 进入项目目录
4. 运行快速启动脚本：
```bash
python start.py
```

### Linux / macOS

1. 安装 Python 3.8+
2. 打开终端
3. 进入项目目录
4. 运行快速启动脚本：
```bash
python3 start.py
```

## 服务器部署

### 使用 systemd (Linux)

1. 创建服务文件 `/etc/systemd/system/qiubot.service`：

```ini
[Unit]
Description=QiuBot Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/QiuBot
ExecStart=/usr/bin/python3 /path/to/QiuBot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. 启用并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable qiubot
sudo systemctl start qiubot
```

3. 查看状态：
```bash
sudo systemctl status qiubot
```

4. 查看日志：
```bash
sudo journalctl -u qiubot -f
```

### 使用 screen (Linux)

1. 安装 screen：
```bash
sudo apt-get install screen  # Debian/Ubuntu
sudo yum install screen       # CentOS/RHEL
```

2. 创建新会话：
```bash
screen -S qiubot
```

3. 在会话中启动 Bot：
```bash
cd /path/to/QiuBot
python3 main.py
```

4. 分离会话：按 `Ctrl+A` 然后按 `D`

5. 重新连接会话：
```bash
screen -r qiubot
```

6. 查看所有会话：
```bash
screen -ls
```

### 使用 tmux (Linux/macOS)

1. 安装 tmux：
```bash
sudo apt-get install tmux  # Debian/Ubuntu
brew install tmux          # macOS
```

2. 创建新会话：
```bash
tmux new -s qiubot
```

3. 在会话中启动 Bot：
```bash
cd /path/to/QiuBot
python3 main.py
```

4. 分离会话：按 `Ctrl+B` 然后按 `D`

5. 重新连接会话：
```bash
tmux attach -t qiubot
```

### 使用 Docker

1. 创建 Dockerfile：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY . .

CMD ["python", "main.py"]
```

2. 构建镜像：
```bash
docker build -t qiubot .
```

3. 运行容器：
```bash
docker run -d --name qiubot --restart unless-stopped qiubot
```

4. 查看日志：
```bash
docker logs -f qiubot
```

5. 停止容器：
```bash
docker stop qiubot
```

## 云服务器部署

### 阿里云 ECS

1. 购买 ECS 实例（推荐配置：1核2G）
2. 选择操作系统（推荐 Ubuntu 20.04）
3. 配置安全组，开放必要端口
4. SSH 连接到服务器
5. 按照 Linux 部署步骤操作

### 腾讯云 CVM

1. 购买 CVM 实例
2. 选择操作系统
3. 配置防火墙规则
4. SSH 连接到服务器
5. 按照 Linux 部署步骤操作

### AWS EC2

1. 创建 EC2 实例
2. 选择 AMI（推荐 Ubuntu）
3. 配置安全组
4. 下载密钥对
5. SSH 连接到实例
6. 按照 Linux 部署步骤操作

## 自动重启

### 使用 supervisor (推荐)

1. 安装 supervisor：
```bash
sudo apt-get install supervisor
```

2. 创建配置文件 `/etc/supervisor/conf.d/qiubot.conf`：

```ini
[program:qiubot]
command=/usr/bin/python3 /path/to/QiuBot/main.py
directory=/path/to/QiuBot
user=your_username
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/qiubot.log
```

3. 更新配置：
```bash
sudo supervisorctl reread
sudo supervisorctl update
```

4. 管理服务：
```bash
sudo supervisorctl start qiubot
sudo supervisorctl stop qiubot
sudo supervisorctl restart qiubot
sudo supervisorctl status qiubot
```

## 日志管理

### 配置日志轮转

创建 `/etc/logrotate.d/qiubot`：

```
/var/log/qiubot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

## 监控和告警

### 使用 cron 定时检查

创建检查脚本 `check_bot.sh`：

```bash
#!/bin/bash

if ! pgrep -f "python.*main.py" > /dev/null; then
    echo "Bot is not running, restarting..."
    cd /path/to/QiuBot
    nohup python3 main.py > /dev/null 2>&1 &
fi
```

添加到 crontab：
```bash
crontab -e
# 每5分钟检查一次
*/5 * * * * /path/to/check_bot.sh
```

## 性能优化

### 内存优化

如果服务器内存有限：

1. 使用轻量级 Python 解释器
2. 定期清理日志文件
3. 限制并发连接数

### 网络优化

1. 使用国内镜像源
2. 配置 DNS 加速
3. 使用 CDN 加速资源访问

## 安全建议

1. 使用非 root 用户运行 Bot
2. 配置防火墙，只开放必要端口
3. 定期更新系统和依赖
4. 不要在代码中硬编码敏感信息
5. 使用环境变量或配置文件管理密钥
6. 定期备份数据

## 备份策略

### 自动备份脚本

创建 `backup.sh`：

```bash
#!/bin/bash

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据目录
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" /path/to/QiuBot/data

# 保留最近7天的备份
find "$BACKUP_DIR" -name "data_*.tar.gz" -mtime +7 -delete
```

添加到 crontab：
```bash
# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

## 故障排查

### Bot 无法启动

1. 检查 Python 版本
2. 检查依赖是否安装
3. 查看错误日志
4. 检查端口是否被占用

### Bot 频繁重启

1. 检查内存使用情况
2. 查看错误日志
3. 检查网络连接
4. 验证 QQ 登录状态

### 消息无法发送

1. 检查 Bot 是否在线
2. 验证目标用户/群组是否存在
3. 检查权限设置
4. 查看 API 调用日志

## 更新部署

### 更新代码

```bash
cd /path/to/QiuBot
git pull origin main
pip install -r requirements.txt -U
sudo systemctl restart qiubot
```

### 回滚版本

```bash
cd /path/to/QiuBot
git checkout <previous-commit>
sudo systemctl restart qiubot
```

---

如有问题，请查看 FAQ.md 或提交 Issue。
