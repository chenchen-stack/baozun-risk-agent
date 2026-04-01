# 本机构建镜像并推送到阿里云 ACR（需已安装 Docker Desktop）
# 用法见下方 param；也可全部用环境变量（适合 CI）
param(
    [string]$Registry = $env:ALIYUN_ACR_REGISTRY,      # 例: registry.cn-hangzhou.aliyuncs.com
    [string]$Namespace = $env:ALIYUN_ACR_NAMESPACE,  # 例: mycompany
    [string]$Repo = $(if ($env:ALIYUN_ACR_REPO) { $env:ALIYUN_ACR_REPO } else { "baozun-risk-agent" }),
    [string]$Tag = $(if ($env:ALIYUN_ACR_TAG) { $env:ALIYUN_ACR_TAG } else { "v1" }),
    [string]$Username = $env:ALIYUN_ACR_USERNAME,
    [string]$Password = $env:ALIYUN_ACR_PASSWORD
)

$ErrorActionPreference = "Stop"
$AgentApp = Split-Path $PSScriptRoot -Parent
Set-Location $AgentApp

function Need([string]$v, [string]$name) {
    if ([string]::IsNullOrWhiteSpace($v)) {
        Write-Host "缺少 $name。请设置环境变量或在参数中传入。" -ForegroundColor Red
        Write-Host "  ALIYUN_ACR_REGISTRY   例: registry.cn-hangzhou.aliyuncs.com" -ForegroundColor Yellow
        Write-Host "  ALIYUN_ACR_NAMESPACE  ACR 命名空间" -ForegroundColor Yellow
        Write-Host "  ALIYUN_ACR_USERNAME   通常是阿里云账号全名" -ForegroundColor Yellow
        Write-Host "  ALIYUN_ACR_PASSWORD   ACR 固定密码或临时令牌" -ForegroundColor Yellow
        Write-Host "可选: ALIYUN_ACR_REPO (默认 baozun-risk-agent), ALIYUN_ACR_TAG (默认 v1)" -ForegroundColor DarkGray
        exit 1
    }
}

Need $Registry "ALIYUN_ACR_REGISTRY"
Need $Namespace "ALIYUN_ACR_NAMESPACE"
Need $Username "ALIYUN_ACR_USERNAME"
Need $Password "ALIYUN_ACR_PASSWORD"

$FullImage = "${Registry}/${Namespace}/${Repo}:${Tag}"
$LocalTag = "baozun-risk-agent:build"

Write-Host ""
Write-Host "=== 构建镜像 ===" -ForegroundColor Cyan
docker build -t $LocalTag -t $FullImage .

Write-Host ""
Write-Host "=== 登录 ACR ===" -ForegroundColor Cyan
$passPlain = $Password
echo $passPlain | docker login --username $Username --password-stdin $Registry
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== 推送 ===" -ForegroundColor Cyan
docker push $FullImage
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "推送完成: $FullImage" -ForegroundColor Green
Write-Host ""
Write-Host "=== 请在 ECS 上执行（已安装 Docker；勿把密码贴到聊天软件）===" -ForegroundColor White
Write-Host @"

# 1) 登录 ACR（与本地相同的用户名/密码，用密码管道或交互输入）
echo \"你的ACR密码\" | sudo docker login --username $Username --password-stdin $Registry

# 2) 拉取并运行
sudo docker pull $FullImage
sudo docker stop baozun-agent 2>/dev/null; sudo docker rm baozun-agent 2>/dev/null
sudo docker run -d --name baozun-agent --restart unless-stopped \\
  -p 8800:8800 -e PORT=8800 -e DEEPSEEK_API_KEY=\"你的DeepSeek密钥\" \\
  $FullImage

# 3) 安全组放行 TCP 8800 后访问 http://ECS公网IP:8800/
"@ -ForegroundColor Yellow

Write-Host ""
Write-Host "也可将 ecs-run.sh 上传到 ECS 后执行（需先编辑其中的镜像与密钥）。" -ForegroundColor DarkGray
