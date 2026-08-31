# 丘Bot (QiuBot)

基于 [NcatBot](https://docs.ncatbot.xyz/) 开发的 QQ 群机器人，专为 The Bazaar 中文社区设计。

## 截图预览

| 物品查询 | 胜率统计 |
|---------|---------|
| ![物品查询](docs/screenshots/item-query.jpg) | ![胜率统计](docs/screenshots/web-ui.jpg) |

**Web 查询页面**

![Web UI](docs/screenshots/winrate.jpg)

---

## 功能概览

### 🎮 The Bazaar 插件（`#bz`）

The Bazaar 游戏数据查询，所有命令以 `#bz` 开头（也支持 `/巴扎`、`/大巴扎`）。

#### 游戏数据查询

| 命令 | 说明 |
|------|------|
| `#bz <物品名>` | 查询物品详情（支持中英文、模糊匹配） |
| `#bz skill <技能名>` | 查询技能详情 |
| `#bz search <关键词>` | 搜索物品/技能 |
| `#bz npc <名称>` | 查询 NPC/商人信息 |
| `#bz day <日期>` | 查询每日商店（1-10 或 event） |
| `#bz boss <名称>` | 查询 Boss/关卡信息 |
| `#bz item <名称>` | 按英文名精确查询物品 |

#### 玩家数据

| 命令 | 说明 |
|------|------|
| `#bz me <用户名>` | 查询玩家最近战绩 |
| `#bz stat <用户名>` | 查询玩家详细数据统计 |
| `#bz history <用户名> [--cb]` | 玩家胜率历史趋势图（`--cb` 色盲模式） |
| `#bz db <卡牌名>` | 查询 BazaarDB 社区数据（支持中英文） |

#### 阵容与胜率分析

| 命令 | 说明 |
|------|------|
| `#bz runs [筛选条件]` | 查询玩家阵容记录 |
| `#bz winrate <卡牌> [+卡牌2] [英雄] [--days N]` | 卡牌 10 胜率统计，支持多卡组合、指定英雄、时间范围 |
| `#bz partner <卡牌> [--days N]` | 卡牌搭档出现率分析 |
| `#bz topcard <职业> [N] [--days D]` | 职业专属卡牌胜率榜（Top N，默认 10） |

#### 其他

| 命令 | 说明 |
|------|------|
| `#bz alias <别名> <卡牌名>` | 设置卡牌自定义别名 |
| `#bz alias hero <别名> <英雄名>` | 设置英雄自定义别名 |
| `#bz alias del <别名>` | 删除别名 |
| `#bz alias list` | 查看所有别名 |
| `#bz watch <用户名>` | 订阅玩家战绩推送（群内使用） |
| `#bz unwatch <用户名>` | 取消订阅 |
| `#bz watchlist` | 查看本群订阅列表 |
| `#bz help` | 查看帮助 |
| `#bz status` | 查看数据源状态 |

**示例：**
```
#bz 火炮阵列
#bz winrate 火炮阵列+赛博铁尺 海盗 --days 7
#bz partner 武装核心
#bz topcard 海盗 10 --days 14
#bz history PlayerName
#bz watch PlayerName
```

---

### 🌐 Web 查询页面

运行在服务器 1027 端口，提供可视化数据查询界面。

| 页面 | 路径 | 说明 |
|------|------|------|
| 阵容查询 | `/runs` | 按英雄、卡牌、胜场、时间筛选阵容列表；支持阵容分析（FP-Growth 挖掘同现卡组）和阵容分享截图 |
| 胜率对比 | `/winrate` | 多卡组合 10 胜率查询，支持多英雄横向对比 |
| 搭档分析 | `/partner` | 卡牌共现率与搭档胜率分析 |
| 职业榜单 | `/topcard` | 各职业专属卡牌胜率榜 + FP-Growth 阵容挖掘 |
| 数据看板 | `/` | 阵容库概况：总局数、英雄分布、每日采集趋势 |
| 冷知识 | `/trivia` | 社区征集的 The Bazaar 游戏冷知识，支持投票 |
| 赞助支持 | `/support` | 赞助者名单与项目支持信息 |

---

### 📝 群聊总结

`@bot 总结最近 X 小时 / 总结今天 / 总结昨天`

由 Claude AI 驱动，按话题分组总结群聊内容，每群每 60 秒最多触发一次，最长支持 24 小时。

### 💬 @对话（可选）

@bot 直接对话，由 Claude AI 回复。默认关闭，可在 `chat_plugin.py` 中设置 `CHAT_ENABLED = True` 开启。

### 🤖 基础功能

- 自我介绍：发送「你是谁」触发
- RBAC 权限系统：支持 user / admin / root 多级权限
- 管理员指令：`#bz admin status/disable/enable/compact`

---

## 数据采集

玩家阵容数据由 Windows 定时任务每 2 小时自动从 [bazaardb.gg](https://bazaardb.gg/) 采集，写入本地 SQLite 数据库，并每日备份至腾讯云 COS（保留最近 3 天 + 赛季前快照）。

---

## 环境要求

- Python >= 3.10
- NcatBot（WebSocket 模式）
- NapCat（QQ 协议端）

## 部署

```bash
git clone https://github.com/CodeHuba/QiuBot.git
cd QiuBot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

配置文件：`config.yaml`

```yaml
napcat:
  ws_uri: ws://localhost:3002
  ws_token: <token>
```

服务以 systemd 管理：

```bash
sudo systemctl start/stop/restart qiubot
sudo journalctl -u qiubot -f
```

Web 服务独立启动：

```bash
cd web_runs
nohup venv/bin/python app.py > logs/web.log 2>&1 &
```

---

## 项目结构

```
QiuBot/
├── main.py
├── config.yaml
├── plugins/
│   ├── bazaar_plugin/
│   │   ├── bazaar_plugin.py         # 指令路由与响应
│   │   ├── gamedata_client.py       # 本地 GameData.db 查询
│   │   ├── bazaardb_client.py       # BazaarDB 社区数据 API
│   │   ├── runs_query.py            # 玩家阵容/胜率/搭档/阵容挖掘
│   │   ├── translations.py          # 中英文翻译（社区维护）
│   │   ├── formatter.py             # 卡牌信息格式化
│   │   ├── chart.py                 # 胜率趋势图生成
│   │   ├── subscriptions.py         # 玩家战绩订阅推送
│   │   └── cache/                   # GameData.db / card_images.json 等
│   ├── summary_plugin/              # 群聊总结（Claude AI）
│   ├── chat_plugin/                 # @对话（Claude AI，默认关闭）
│   ├── qiu_plugin/                  # 基础指令
│   └── dev_plugin/                  # 开发调试
├── data/
│   ├── bazaar_runs.db               # 玩家阵容数据库（SQLite）
│   └── rbac.json                    # 权限配置
├── tools/
│   ├── backup_bazaar_db.sh          # 每日备份脚本（上传 COS，保留 3 天）
│   └── season_update.sh             # 赛季更新 SOP 脚本
└── web_runs/                        # Web 查询页面（Flask，1027 端口）
    ├── app.py
    └── static/
        ├── runs.html                # 阵容查询
        ├── topcard.html             # 职业榜单
        ├── winrate.html             # 胜率对比
        ├── partner.html             # 搭档分析
        ├── trivia.html              # 冷知识
        └── support.html             # 赞助支持
```

---

## 相关链接

- [NcatBot 文档](https://docs.ncatbot.xyz/)
- [BazaarDB](https://bazaardb.gg/)
- [The Bazaar](https://www.howbazaar.gg/)
