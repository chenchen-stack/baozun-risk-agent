@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在打包到桌面：宝尊风控Agent-钉钉分享.zip （不含 .venv 与 .env）...
python scripts\pack_for_dingtalk.py
if errorlevel 1 (
  echo 若提示找不到 python，请先安装 Python 3.10+ 并加入 PATH。
  pause
  exit /b 1
)
echo.
pause
