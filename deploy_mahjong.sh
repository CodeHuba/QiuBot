#!/bin/bash
# 麻将插件快速部署脚本

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     麻将牌谱分析插件 - 快速部署                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查 Python
echo "1. 检查 Python 环境..."
python --version 2>/dev/null || python3 --version 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Python 未安装"
    exit 1
fi
echo "✅ Python 已安装"
echo ""

# 检查文件
echo "2. 检查文件完整性..."
FILES=(
    "plugins/qiu_plugin/mahjong/__init__.py"
    "plugins/qiu_plugin/mahjong/models.py"
    "plugins/qiu_plugin/mahjong/mortal_analyzer.py"
    "plugins/qiu_plugin/mahjong/task_manager.py"
    "plugins/qiu_plugin/mahjong/mahjong_plugin.py"
    "data/mahjong/config.json"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file 缺失"
        exit 1
    fi
done
echo ""

# 检查目录
echo "3. 检查目录..."
if [ -d "data/mahjong/excel" ]; then
    echo "✅ data/mahjong/excel/"
else
    echo "⚠️  创建目录: data/mahjong/excel/"
    mkdir -p data/mahjong/excel
fi
echo ""

# 安装依赖
echo "4. 安装依赖..."
echo "正在安装: selenium, undetected-chromedriver, openpyxl"
pip install selenium undetected-chromedriver openpyxl
if [ $? -eq 0 ]; then
    echo "✅ 依赖安装成功"
else
    echo "❌ 依赖安装失败"
    exit 1
fi
echo ""

# 检查 Chrome
echo "5. 检查 Chrome 浏览器..."
if command -v google-chrome &> /dev/null || command -v chrome &> /dev/null; then
    echo "✅ Chrome 已安装"
else
    echo "⚠️  未检测到 Chrome，请确保已安装 Chrome 浏览器"
fi
echo ""

# 完成
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     部署完成！                                             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 启动 Bot:"
echo "   python start.py"
echo ""
echo "🎮 测试命令:"
echo "   /mahjong 18558711 5"
echo ""
echo "📚 查看文档:"
echo "   - 快速开始: MAHJONG_QUICKSTART.md"
echo "   - 详细文档: plugins/qiu_plugin/mahjong/README.md"
echo "   - 错误修复: ERROR_FIX_REPORT.md"
echo ""
