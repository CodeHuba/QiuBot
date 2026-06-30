# 麻将牌谱分析插件 - 快速开始

## 安装步骤

### 1. 安装依赖
```bash
cd /d/PJ/QiuBot
pip install selenium undetected-chromedriver openpyxl
```

### 2. 确保 Chrome 浏览器已安装
- 需要 Chrome 90 或更高版本
- undetected-chromedriver 会自动下载对应的 ChromeDriver

### 3. 启动 Bot
```bash
python start.py
```

## 使用方法

### 基本命令
```
/mahjong <玩家ID> [数量]
```

### 示例
```
/mahjong 18558711           # 分析50场（默认）
/mahjong 18558711 30        # 分析30场
/mahjong 18558711 100       # 分析100场
```

## 功能特性

- ✅ 无头模式运行（后台执行）
- ✅ 异步执行，不阻塞机器人
- ✅ 进度通知（25%、50%、75%）
- ✅ 自动发送 Excel 分析报告
- ✅ 频率限制：3次/24小时/用户
- ✅ 单任务模式，避免资源竞争

## 配置文件

位置：`data/mahjong/config.json`

关键配置项：
- `browser.headless`: 是否无头模式（true=后台运行）
- `analysis.default_count`: 默认分析场数（50）
- `analysis.max_count`: 最大分析场数（100）
- `rate_limit.max_requests_per_user`: 频率限制（3次）

## 输出文件

Excel 文件保存在：`data/mahjong/excel/`

文件名格式：`牌谱分析_<玩家ID>_<时间戳>.xlsx`

## 注意事项

1. 首次运行会自动下载 ChromeDriver，可能需要几分钟
2. 分析过程中请保持网络连接稳定
3. 10场约需2-3分钟，50场约需5-10分钟
4. 如遇到 Cloudflare 验证，插件会自动处理

## 故障排除

### 问题：提示依赖未安装
解决：运行 `pip install selenium undetected-chromedriver openpyxl`

### 问题：Chrome 启动失败
解决：确保系统已安装 Chrome 浏览器

### 问题：任务一直卡住
解决：检查网络连接，任务会自动重试3次

### 问题：频率限制
解决：等待24小时后重置，或修改配置文件

## 更多信息

详细文档：`plugins/qiu_plugin/mahjong/README.md`
