#!/usr/bin/env bash
# 供 init / passwd 共用的配置生成逻辑

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT}/.env"
CADDYFILE="${ROOT}/caddy/Caddyfile"

normalize_domains_csv() {
  echo "$1" | tr '，' ',' | sed 's/[[:space:]]*,[[:space:]]*/,/g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

normalize_domains_for_caddy() {
  echo "$1" | tr '，' ',' | sed 's/, */, /g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

is_localhost_only() {
  local csv
  csv="$(normalize_domains_csv "$1")"
  [[ "$csv" == "localhost" || "$csv" == "127.0.0.1" || -z "$csv" ]]
}

primary_domain() {
  local csv
  csv="$(normalize_domains_csv "$1")"
  echo "${csv%%,*}"
}

generate_bcrypt_hash() {
  ensure_docker
  docker run --rm caddy:alpine caddy hash-password --plaintext "$1"
}

ensure_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "错误: 未找到 docker，请先安装 Docker。" >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "错误: Docker 守护进程未运行，请先启动 Docker。" >&2
    exit 1
  fi
}

escape_dollar_for_caddy() {
  echo "$1" | sed 's/\$/$$/g'
}

read_env_value() {
  local key="$1"
  if [[ ! -f "$ENV_FILE" ]]; then
    return 1
  fi
  grep -E "^${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '\r'
}

write_env() {
  local domains_csv="$1"
  local admin_user="${2:-admin}"
  local normalized
  normalized="$(normalize_domains_csv "$domains_csv")"

  umask 077
  cat >"$ENV_FILE" <<EOF
HOST_DOMAIN=${normalized}
CADDY_ADMIN_USER=${admin_user}
EOF
}

write_caddyfile() {
  local domains_csv="$1"
  local admin_user="$2"
  local plaintext_password="$3"

  local hash hash_escaped domains_caddy
  hash="$(generate_bcrypt_hash "$plaintext_password")"
  hash_escaped="$(escape_dollar_for_caddy "$hash")"
  domains_caddy="$(normalize_domains_for_caddy "$domains_csv")"

  umask 077
  cat >"$CADDYFILE" <<EOF
(vpc_handlers) {

    @v2ws {
        path /api
        header Connection *pgrade*
        header Upgrade *ebsocket*
    }
    reverse_proxy @v2ws v2ray:58888

    @panel {
        path_regexp panel_route ^/panel(/.*)?\$\$|^/assets/
    }
    handle @panel {
        basicauth {
            ${admin_user} ${hash_escaped}
        }
        reverse_proxy panel:8000
    }

    @site_root path /
    handle @site_root {
        root * /usr/share/caddy
        file_server
    }

    log {
        format console
    }
}

http://localhost http://127.0.0.1 {
    import vpc_handlers
}
EOF

  if ! is_localhost_only "$domains_csv"; then
    cat >>"$CADDYFILE" <<EOF

${domains_caddy} {
    import vpc_handlers
}
EOF
  fi
}

prompt_password() {
  local pw pw2
  while true; do
    read -rsp "管理密码: " pw
    echo
    read -rsp "确认密码: " pw2
    echo
    if [[ -z "$pw" ]]; then
      echo "密码不能为空。" >&2
      continue
    fi
    if [[ "$pw" != "$pw2" ]]; then
      echo "两次输入不一致，请重试。" >&2
      continue
    fi
    PASSWORD="$pw"
    return 0
  done
}

prompt_domains() {
  local input
  while true; do
    read -rp "域名 (逗号分隔，本地试跑可填 localhost): " input
    input="$(normalize_domains_csv "$input")"
    if [[ -n "$input" ]]; then
      DOMAINS="$input"
      return 0
    fi
    echo "域名不能为空。" >&2
  done
}

print_overview() {
  local domains_csv="$1"
  local admin_user="$2"
  local admin_password="$3"
  local primary panel_url

  primary="$(primary_domain "$domains_csv")"
  if is_localhost_only "$domains_csv"; then
    panel_url="http://${primary}/panel/"
  else
    panel_url="https://${primary}/panel/"
  fi

  cat <<EOF

========================================
配置完成
========================================
域名:       $(normalize_domains_for_caddy "$domains_csv")
管理员账号: ${admin_user}
管理员密码: ${admin_password}
管理地址:   ${panel_url}
.env:       ${ENV_FILE}
Caddyfile:  ${CADDYFILE}

下一步:
  docker compose up -d --build

修改密码后请重启 Caddy:
  docker compose restart caddy
========================================
EOF
}
