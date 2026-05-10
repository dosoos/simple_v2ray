#!/usr/bin/env bash
# 示例：测试主节点 sync/users（使用节点 Bearer，且该节点须已在后台启用）
set -euo pipefail
BASE="${1:-https://localhost}"
BEARER="${2:-}"

if [[ -z "$BEARER" ]]; then
  echo "用法: $0 <站点根URL> <bearer_token>"
  exit 1
fi

curl -sS -G "${BASE}/api/v1/sync/users/" \
  --data-urlencode "since=0" \
  -H "Authorization: Bearer ${BEARER}" \
  -H "Accept: application/json" | head -c 2000
echo
