#!/usr/bin/env bash
# 调用示例（需携带与管理后台一致的 Basic 账号密码）
set -euo pipefail
BASE="${1:-http://127.0.0.1}"
USER="${2:-admin}"
PASS="${3:-changeme}"

curl -sS -u "${USER}:${PASS}" "${BASE}/panel/api/config" | head -c 4000
echo
