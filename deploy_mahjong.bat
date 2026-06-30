@echo off
REM 麻将插件快速部署脚本 (Windows)

echo ╔════════════════════════════════════════════════════════════╗
echo ║     麻将牌谱分析插件 - 快速部署                           ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 检查 Python
echo 1. 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python 未安装
    pause
    exit /b 1
)
python --version
echo ✅ Python 已安装
echo.

REM 检查文件
echo 2. 检查文件完整性...
set FILES=plugins\qiu_plugin\mahjong\__init__.py plugins\qiu_plugin\mahjong\models.py plugins\qiu_plugin\mahjong\mortal_analyzer.py plugins\qiu_plugin\mahjong\task_manager.py plugins\qiu_plugin\mahjong\mahjong_plugin.py data\mahjong\config.json

for %%f in (%FILES%) do (
    if exist "%%f" (
        echo ✅ %%f
    ) else (
        echo ❌ %%f 缺失
        pause
        exit /b 1
    )
)
echo.

REM 检查目录
echo 3. 检查目录...
if exist "data\mahjong\excel" (
    echo ✅ data\mahjong\excel\
) else (
    echo ⚠️  创建目录: data\mahjong\excel\
    mkdir data\mahjong\excel
)
echo.

REM 安装依赖
echo 4. 安装依赖...
echo 正在安装: selenium, undetected-chromedriver, openpyxl
pip install selenium undetected-chromedriver openpyxl
if %errorlevel% equ 0 (
    echo ✅ 依赖安装成功
) else (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)
echo.

REM 检查 Chrome
echo 5. 检查 Chrome 浏览器...
where chrome >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Chrome 已安装
) else (
    echo ⚠️  未检测到 Chrome，请确保已安装 Chrome 浏览器
)
echo.

REM 完成
echo ╔════════════════════════════════════════════════════════════╗
echo ║     部署完成！                                             ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 🚀 启动 Bot:
echo    python start.py
echo.
echo 🎮 测试命令:
echo    /mahjong 18558711 5
echo.
echo 📚 查看文档:
echo    - 快速开始: MAHJONG_QUICKSTART.md
echo    - 详细文档: plugins\qiu_plugin\mahjong\README.md
echo    - 错误修复: ERROR_FIX_REPORT.md
echo.
pause
