#!/usr/bin/env bash
# 生成 bcrypt 并写入 caddy/admin.hash（不经 .env，无 $ 转义问题）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HASH_FILE="${ROOT}/caddy/admin.hash"

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <明文密码>"
  echo "将把哈希写入 ${HASH_FILE}（单行），然后请执行: docker compose restart caddy"
  exit 1
fi

HASH="$(docker run --rm caddy:2-alpine caddy hash-password --plaintext "$1")"

umask 077
printf '%s\n' "$HASH" >"$HASH_FILE"

echo "已写入 ${HASH_FILE}"
echo "哈希（应与文件内容一致）："
echo "$HASH"
echo ""
echo "重启 Caddy 后使用新密码登录：docker compose restart caddy"
