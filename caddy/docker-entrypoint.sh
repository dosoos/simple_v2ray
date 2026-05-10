#!/bin/sh
set -e
# 口令哈希来自 caddy/admin.hash（单行 bcrypt）。不在 Caddyfile 里用 {$VAR} 展开哈希，否则 $ 会被 Caddy 二次解析导致校验失败。
USER="${CADDY_ADMIN_USER:-admin}"
HASH=""

if [ -f /etc/caddy/admin.hash ]; then
  line="$(grep -v '^[[:space:]]*#' /etc/caddy/admin.hash | sed '/^[[:space:]]*$/d' | head -1)"
  line="$(printf '%s' "$line" | tr -d '\r\n')"
  # 去掉 UTF-8 BOM（若 Windows 编辑过）
  line="${line#$(printf '\357\273\277')}"
  if [ -n "$line" ]; then
    HASH="$line"
  fi
fi

# 与「docker run caddy hash-password --plaintext changeme」一致（bcrypt 每次盐不同，此为当前仓库选用的固定串）
DEFAULT_HASH='$2a$14$mVsTZSGVsqvlp/4k8ZI7eOXMy.ZJ.JthehVlv0Gpa6fGT0Qh492JG'

if [ -z "$HASH" ]; then
  HASH="$DEFAULT_HASH"
fi

{
  printf '%s\n' 'basicauth {'
  printf '    %s %s\n' "$USER" "$HASH"
  printf '%s\n' '}'
} >/tmp/panel-basicauth.caddy

export HOST_DOMAIN_SITES="$(echo "$HOST_DOMAIN" | tr '，' ',' | sed 's/, */, /g')"
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
