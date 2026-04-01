# 宝尊风控 Agent 演示：启动 Web 并显示可分享的访问地址
# 用法: .\start-demo.ps1              # 本机 + 内网 + 公网隧道命令提示
#       .\start-demo.ps1 -InternalOnly # 仅内网场景（不显示 cloudflared/ngrok）
param([switch]$InternalOnly)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$port = 8800
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "未找到 python，请先安装 Python 并 pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

Write-Host ""
if ($InternalOnly) {
    Write-Host "=== 宝尊风控 AI Agent（仅内网）===" -ForegroundColor Cyan
} else {
    Write-Host "=== 宝尊风控 AI Agent 演示 ===" -ForegroundColor Cyan
}
Write-Host "本机浏览器打开：" -ForegroundColor White
Write-Host "  http://127.0.0.1:$port/" -ForegroundColor Green
Write-Host ""

$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notmatch '^169\.254\.' } |
    Select-Object -ExpandProperty IPAddress -Unique
if ($ips) {
    Write-Host "给同事用的内网地址（须与本机同一局域网 / VPN）：" -ForegroundColor White
    foreach ($ip in $ips) {
        Write-Host "  http://${ip}:$port/" -ForegroundColor Yellow
    }
} else {
    Write-Host "（未检测到内网 IPv4，同事请改用你能 ping 通的本机 IP）" -ForegroundColor DarkYellow
}

Write-Host ""
if ($InternalOnly) {
    Write-Host "若同事打不开：在本机「Windows 安全中心 → 防火墙 → 高级设置」入站规则允许 TCP $port，或临时关闭防火墙测试。" -ForegroundColor DarkGray
    Write-Host ""
} else {
    Write-Host "公网临时链接（需已安装对应工具）：" -ForegroundColor White
    Write-Host "  cloudflared tunnel --url http://127.0.0.1:$port" -ForegroundColor DarkGray
    Write-Host "  ngrok http $port" -ForegroundColor DarkGray
    Write-Host ""
}
Write-Host "说明: 密钥填在 .env 的 DEEPSEEK_API_KEY，或系统环境变量。" -ForegroundColor DarkGray
Write-Host "按 Ctrl+C 停止服务。" -ForegroundColor DarkGray
Write-Host ""

$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $py) {
    & $py -m uvicorn server:app --host 0.0.0.0 --port $port
} else {
    python -m uvicorn server:app --host 0.0.0.0 --port $port
}
