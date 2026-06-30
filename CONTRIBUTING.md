# 贡献指南

感谢你对丘Bot项目的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请：

1. 确认 Bug 是否已经被报告
2. 创建一个新的 Issue，包含：
   - Bug 的详细描述
   - 复现步骤
   - 预期行为和实际行为
   - 环境信息（操作系统、Python 版本、NcatBot 版本）
   - 相关的日志或截图

### 提出新功能

如果你有新功能的想法：

1. 先创建一个 Issue 讨论这个功能
2. 说明功能的用途和使用场景
3. 如果可能，提供实现思路

### 提交代码

1. Fork 本项目
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建一个 Pull Request

### 代码规范

- 使用 Python 3.8+ 语法
- 遵循 PEP 8 代码风格
- 为新功能添加文档字符串
- 为复杂逻辑添加注释
- 保持代码简洁易读

### 提交信息规范

提交信息应该清晰地描述改动内容：

```
类型: 简短描述

详细描述（可选）

相关 Issue: #123
```

类型包括：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建或辅助工具的变动

示例：
```
feat: 添加天气查询功能

实现了通过命令 /weather 查询天气的功能
支持城市名称和城市代码两种查询方式

相关 Issue: #42
```

## 开发环境设置

1. 克隆项目：
```bash
git clone https://github.com/yourusername/QiuBot.git
cd QiuBot
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行测试：
```bash
python test.py
```

4. 开始开发！

## 插件开发指南

查看 `DEVELOPMENT.md` 了解如何开发新插件。

## 问题和讨论

如果你有任何问题或想法，欢迎：
- 创建 Issue
- 发起 Discussion
- 加入我们的 QQ 群

## 行为准则

- 尊重所有贡献者
- 保持友好和专业
- 接受建设性的批评
- 关注对项目最有利的事情

## 许可证

通过贡献代码，你同意你的贡献将在与本项目相同的许可证下发布。

---

再次感谢你的贡献！🎉
