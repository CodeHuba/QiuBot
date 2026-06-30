# 麻将牌谱分析插件

> 为 QiuBot 提供麻将牌谱分析功能，基于 Mortal AI 分析玩家牌谱质量

## 快速开始

### 1. 安装依赖
```bash
pip install selenium undetected-chromedriver openpyxl
```

### 2. 启动 Bot
```bash
python start.py
```

### 3. 使用命令
```
/mahjong 18558711 5
```

## 功能特性

- ✅ **无头模式运行** - 后台执行，不显示浏览器窗口
- ✅ **异步执行** - 不阻塞机器人，可继续使用其他功能
- ✅ **进度通知** - 实时了解分析进度（25%、50%、75%）
- ✅ **自动重试** - 遇到错误自动重试，最多3次
- ✅ **频率限制** - 每用户3次/24小时，防止滥用
- ✅ **Excel报告** - 自动生成并发送分析报告

## 命令格式

```
/mahjong <玩家ID> [数量]
```

**参数说明：**
- `玩家ID`：amae-koromo 网站的玩家ID（必填）
- `数量`：分析场数，可选，默认5场，范围5-100

**示例：**
```
/mahjong 18558711           # 分析5场（默认）
/mahjong 18558711 10        # 分析10场
/mahjong 18558711 50        # 分析50场
```

## 使用流程

```
发送命令 → 收到确认 → 后台执行 → 进度通知 → 收到结果 + Excel文件
```

**预计耗时：**
- 5场：约1-2分钟
- 10场：约2-3分钟
- 50场：约5-10分钟
- 100场：约10-20分钟

## 配置说明

配置文件位于 `data/mahjong/config.json`

**关键配置项：**
```json
{
  "analysis": {
    "default_count": 5,      // 默认分析场数
    "max_count": 100,        // 最大场数
    "min_count": 5           // 最小场数
  },
  "rate_limit": {
    "max_requests_per_user": 3,  // 每用户限制
    "window_hours": 24           // 时间窗口
  }
}
```

## 输出文件

**位置：** `data/mahjong/excel/`

**文件名格式：** `牌谱分析_<玩家ID>_<时间戳>.xlsx`

**内容包括：**
- 牌谱链接
- Rating 值
- 一致率
- Total 值
- Mortal 解析链接

## 使用限制

- **频率限制**：每个用户 3次/24小时
- **场数范围**：5-100场
- **并发限制**：同时只能有1个任务运行

## 常见问题

### Q: 任务一直没有响应？
**A:** 检查网络连接，查看 Bot 日志，等待几分钟。如果超过10分钟仍无响应，可能是任务失败。

### Q: 提示"当前有任务正在执行中"？
**A:** 等待当前任务完成后再试。单任务模式下，一次只能处理一个任务。

### Q: 提示"您已达到使用限制"？
**A:** 等待24小时后重置，或联系管理员修改配置。

### Q: 收不到 Excel 文件？
**A:** 检查 `data/mahjong/excel/` 目录，文件已保存在本地。

## 技术架构

```
用户命令 → 参数验证 → 频率检查 → 任务创建
                                      ↓
                                 后台Worker
                                      ↓
                            线程池执行Selenium
                                      ↓
                              进度回调通知
                                      ↓
                            结果汇总 → 通知用户
```

**核心组件：**
- `MahjongPlugin` - 主插件类，处理命令和通知
- `MahjongTaskManager` - 任务管理器，管理任务生命周期
- `MortalAnalyzer` - Mortal分析器封装，执行实际分析
- `RateLimiter` - 频率限制器，防止滥用

## 文件结构

```
plugins/qiu_plugin/mahjong/
├── __init__.py              # 模块初始化
├── models.py                # 数据模型
├── mortal_analyzer.py       # Mortal分析器封装
├── task_manager.py          # 任务管理器
├── mahjong_plugin.py        # 主插件类
└── README.md                # 技术文档

data/mahjong/
├── config.json              # 配置文件
└── excel/                   # Excel输出目录
```

## 详细文档

- **用户指南**：`MAHJONG_USER_GUIDE.md` ⭐ 推荐首读
- **快速开始**：`MAHJONG_QUICKSTART.md`
- **安装指南**：`MAHJONG_INSTALL.md`
- **错误修复**：`ERROR_FIX_REPORT.md`
- **技术文档**：`plugins/qiu_plugin/mahjong/README.md`
- **完成报告**：`IMPLEMENTATION_COMPLETE.txt`

## 部署脚本

**Windows：**
```bash
deploy_mahjong.bat
```

**Linux/Mac：**
```bash
bash deploy_mahjong.sh
```

部署脚本会自动：
- 检查 Python 环境
- 验证文件完整性
- 安装依赖包
- 检查 Chrome 浏览器
- 显示启动指令

## 环境要求

- Python 3.8+
- Chrome 浏览器 90+
- 稳定的网络连接
- 可访问 amae-koromo.sapk.ch 和 mjai.ekyu.moe

## 依赖包

```
selenium>=4.0.0
undetected-chromedriver>=3.5.0
openpyxl>=3.1.0
```

## 错误修复记录

**问题：** `QiuPlugin.handle_who_are_you() missing 1 required positional argument: 'event'`

**原因：** 使用了错误的装饰器 `@on_message`

**修复：**
- ✅ `qiu_plugin.py`: `@on_message` → `@filter_registry.on_message`
- ✅ `mahjong_plugin.py`: `@on_message` → `@filter_registry.on_message`

详见：`ERROR_FIX_REPORT.md`

## 版本信息

- **版本**：v1.0.0
- **完成时间**：2026-01-27
- **代码行数**：951行
- **文件数量**：18个
- **状态**：✅ 可用

## 技术支持

**问题排查：**
1. 查看 Bot 日志输出
2. 阅读 `ERROR_FIX_REPORT.md`
3. 查看 `MAHJONG_USER_GUIDE.md` 的常见问题部分
4. 检查文件完整性
5. 验证依赖是否正确安装

**日志位置：**
Bot 运行时会在控制台输出详细日志，包括任务创建、执行进度、错误信息等。

## 许可证

遵循 NcatBot 项目的许可证。

---

**快速链接：**
- [用户使用指南](MAHJONG_USER_GUIDE.md) ⭐
- [快速开始](MAHJONG_QUICKSTART.md)
- [错误修复报告](ERROR_FIX_REPORT.md)
- [完成报告](IMPLEMENTATION_COMPLETE.txt)

**最后更新：** 2026-01-27 21:20
