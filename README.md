# 个人简易 VPN 代理（单节点）

轻量单节点方案：**Caddy** 负责 TLS、WebSocket 反代与 **管理页 Basic 认证**；**FastAPI** 直接读写 `v2ray/config.json`（**无数据库**、无多节点）。提供配置编辑、**备份**与**导入/还原**，替代手写 shell 改配置。

## 文档

- 架构示意：`docs/architecture.md`

## 架构（简化）

- **Caddy**：HTTPS、把 `/proxy` 反代到 V2Ray VMess 入站、把 `/panel` 与 `/api/panel` 用 Basic Auth 保护后反代到面板。
- **V2Ray**：使用仓库内 `v2ray/config.json`（可经面板覆盖）。
- **Panel（FastAPI）**：只操作文件，逻辑见 `web/main.py`。

## 快速开始

1. 复制环境变量：`cp .env.example .env`（生产环境请设置强密码的 `CADDY_ADMIN_HASH`，见下）。
2. 启动：`docker compose up -d --build`。
3. 浏览器打开管理页：`https://<HOST_DOMAIN>/panel/`（本机 HTTP：`http://127.0.0.1/panel/`）。  
   - 若未自定义 `CADDY_ADMIN_HASH`，默认用户名为 `admin`、密码为 **`changeme`**（仅试跑，上线前务必修改）。

### 设置管理密码（bcrypt）

```bash
chmod +x scripts/gen-caddy-hash.sh
./scripts/gen-caddy-hash.sh '你的强密码'
# 将输出写入 .env 的 CADDY_ADMIN_HASH=，并 docker compose up -d
```

修改 `config.json` 后，一般需要 **重启 V2Ray** 才能生效：

```bash
docker compose restart v2ray
```

## 环境变量

| 变量 | 含义 |
| --- | --- |
| `HOST_DOMAIN` | Caddy 站点名与 TLS 域名；本地可用 `localhost` |
| `CADDY_ADMIN_USER` | Basic 认证用户名（默认 `admin`） |
| `CADDY_ADMIN_HASH` | 密码的 bcrypt 哈希；不填则使用 compose 内建默认（密码 `changeme`） |

面板进程读取：`V2RAY_CONFIG_PATH`（默认 `/v2ray/config.json`）、`BACKUP_DIR`（默认 `/v2ray/backups`）。

## 本地开发（可选）

```bash
cd web && pip install -r requirements.txt
export V2RAY_CONFIG_PATH="$(pwd)/../v2ray/config.json"
export BACKUP_DIR="$(pwd)/../v2ray/backups"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

管理路由仍需结合 Caddy Basic Auth；直连调试时可暂时注释 Caddy 中的 `basicauth` 块（不推荐在生产环境）。

## 仓库布局

- `web/`：FastAPI 应用与 Dockerfile  
- `caddy/`：`Caddyfile`  
- `v2ray/`：`config.json` 与备份目录（运行时挂载）
