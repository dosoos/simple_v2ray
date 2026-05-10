#!/usr/bin/env bash
set -euo pipefail

# 推荐使用 Docker Compose 一键启动（见 README）
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "使用 docker compose 启动（请先复制 .env.example 为 .env 并填写变量）"
  docker compose up -d --build
  exit 0
fi

echo "未检测到 docker compose，回退到本机直接运行 v2ray + caddy（仅代理，无 Django 后台）"
apt-get update
apt-get install -y jq uuid-runtime

docker run \
  -d \
  --restart=always \
  --name v2ray \
  -v "$(pwd)/v2ray:/etc/v2ray" \
  -v "$(pwd)/v2ray/log:/var/log/v2ray" \
  v2fly/v2fly-core run -c /etc/v2ray/config.json

docker run \
  -d \
  --restart=always \
  --name caddy \
  --link v2ray \
  -v "$(pwd)/caddy/Caddyfile:/etc/caddy/Caddyfile" \
  -v "$(pwd)/caddy/data:/data" \
  -v "$(pwd)/caddy/config:/config" \
  -p 80:80 \
  -p 443:443 \
  caddy:alpine
