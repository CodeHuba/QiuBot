@echo off
cd /d "%~dp0"
chcp 936 > nul

echo =====================================
echo            QiuBot 启动器
echo =====================================
echo.

py -3.11 -c "import ncatbot" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 未找到，或未安装 ncatbot
    pause
    exit /b 1
)

echo [1/3] 检查 NapCat WebSocket...
netstat -ano | findstr ":3001" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [警告] NapCat 未启动 ^(3001 端口未监听^)
    echo 请先以管理员运行 NapCat.Shell\napiLoader.bat
    pause
    exit /b 1
)
echo       OK - 3001 端口已监听
echo.

echo [2/3] 启动 QiuBot...
echo [3/3] 日志输出 (Ctrl+C 停止):
echo -------------------------------------
py -3.11 main.py

echo.
echo -------------------------------------
echo QiuBot 已停止
pause
