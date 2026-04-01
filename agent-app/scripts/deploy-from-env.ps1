# 从 agent-app\env.deploy 读取变量后执行推送（文件勿提交 Git）
$ErrorActionPreference = "Stop"
$AgentApp = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $AgentApp "env.deploy"
if (-not (Test-Path $envFile)) {
    Write-Host "未找到 env.deploy。请复制 env.deploy.example 为 env.deploy 并填写 ACR 信息。" -ForegroundColor Red
    exit 1
}
Get-Content $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^\s*#' -or $line -eq '') { return }
    if ($line -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$') {
        $k = $matches[1]
        $v = $matches[2].Trim()
        if (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'"))) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        Set-Item -Path "env:$k" -Value $v
    }
}
& "$PSScriptRoot\deploy-aliyun.ps1"
