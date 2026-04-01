@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 第一次使用：复制 env.deploy.example 为 env.deploy，填写 ACR 与密码；并安装 Docker Desktop。
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\deploy-from-env.ps1"
echo.
pause
