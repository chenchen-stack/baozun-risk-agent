@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========== 宝尊风控 Agent：安装依赖并启动 ==========
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 python，请先安装 Python 3.10+ 并勾选 Add to PATH。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 创建虚拟环境 .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败。
    pause
    exit /b 1
  )
)

echo [2/3] 安装依赖（首次较慢）...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [错误] pip 安装失败，请检查网络或 pip 源。
  pause
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [首次] 已创建 .env，正在打开记事本——请填写 DEEPSEEK_API_KEY=你的密钥，保存并关闭记事本。
  echo 然后请再次双击本脚本启动服务。
  echo.
  notepad ".env"
  pause
  exit /b 0
)

echo [3/3] 启动服务：浏览器打开 http://127.0.0.1:8800/  （勿关闭本窗口）
echo.
".venv\Scripts\python.exe" -m uvicorn server:app --host 0.0.0.0 --port 8800
pause
