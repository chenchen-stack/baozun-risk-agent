#!/usr/bin/env bash
# 在阿里云 ECS（Alibaba Cloud Linux / Ubuntu）上执行：先编辑下面三行，再 sudo bash ecs-run.sh
set -euo pipefail

# ─── 按你的实际情况修改 ───
FULL_IMAGE="registry.cn-hangzhou.aliyuncs.com/你的命名空间/baozun-risk-agent:v1"
ACR_USER="你的ACR用户名"
ACR_PASS="你的ACR密码或临时令牌"
DEEPSEEK_API_KEY="你的DeepSeek_API密钥"
REGISTRY="${FULL_IMAGE%%/*}"
# ─────────────────────────

if command -v docker &>/dev/null; then
  :
else
  if [ -f /etc/os-release ] && grep -qi alinux /etc/os-release; then
    sudo yum install -y docker
  elif command -v apt-get &>/dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y docker.io
  else
    echo "请手动安装 Docker 后重试"
    exit 1
  fi
  sudo systemctl enable --now docker
fi

echo "$ACR_PASS" | sudo docker login --username "$ACR_USER" --password-stdin "$REGISTRY"
sudo docker pull "$FULL_IMAGE"
sudo docker stop baozun-agent 2>/dev/null || true
sudo docker rm baozun-agent 2>/dev/null || true
sudo docker run -d --name baozun-agent --restart unless-stopped \
  -p 8800:8800 \
  -e PORT=8800 \
  -e DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
  "$FULL_IMAGE"

echo "已启动。请访问 http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8800/ （确保安全组放行 8800）"
