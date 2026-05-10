#!/usr/bin/env bash
# 生成 Caddy basicauth 所需的 bcrypt，写入 .env 中的 CADDY_ADMIN_HASH=
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "用法: $0 <明文密码>"
  echo "将输出的哈希复制到 .env 的 CADDY_ADMIN_HASH="
  exit 1
fi
exec docker run --rm caddy:2-alpine caddy hash-password --plaintext "$1"
