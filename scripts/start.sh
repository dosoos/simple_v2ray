#!/usr/bin/env bash
set -euo pipefail

echo "使用 Docker Compose 启动 panel + v2ray + caddy（请先复制 .env.example 为 .env）"
docker compose up -d --build
