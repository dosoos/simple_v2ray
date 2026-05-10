# 个人简易 VPN 代理（单节点）

轻量单节点方案：**Caddy** 负责 TLS、WebSocket 反代与 **管理页 Basic 认证**；**FastAPI** 直接读写 `v2ray/config.json`（**无数据库**）。管理后台使用仓库内 **Sneat** 静态资源（`web/sneat-1.0.0/assets`，挂载 **`/assets/`**），**表格管理** VMess 用户（`alterId` / `level` 固定为 0，无需用户填写）；支持 **导出 / 导入**：**导出**为**完整** `config.json`；**导入**也请使用**完整备份 JSON**（可与导出文件相同），面板**仅提取其中 VMess 入站 `clients`** 做合并/同步，**其它字段全部忽略**；默认 **合并用户**，可选 **同步列表**（以导入为准替换 VMess 用户数组）。

## 文档

- 架构示意：`docs/architecture.md`

## 架构（简化）

- **Caddy**：HTTPS、把 `/proxy` 反代到 V2Ray VMess 入站；把 **`/panel`、`/api/panel`、`/assets`** 用 Basic Auth 保护后反代到面板（避免 Sneat 静态资源绕开路由）。
- **V2Ray**：使用仓库内 `v2ray/config.json`（可经面板覆盖）。
- **Panel（FastAPI）**：只操作文件；Sneat 样式挂载为 `/assets/*`，逻辑见 `web/main.py`、`web/v2ray_config.py`。

## 快速开始

1. 复制环境变量：`cp .env.example .env`。若仍使用旧的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`，请改为 **`CADDY_ADMIN_USER` + `CADDY_ADMIN_HASH`**（见 `.env.example`）。bcrypt 哈希里的 `$` 在 `.env` 中建议用**单引号**包住整段哈希，避免被 Compose 解析成变量。
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

Stats API（`V2RAY_API_HOST`/`V2RAY_API_PORT`，默认 **`v2ray`/`10085`**）与按月流量（`TRAFFIC_STORE_PATH`、`TRAFFIC_POLL_*`、`TRAFFIC_MONTH_TZ` 等）由应用代码内置默认值；需要覆盖时在本地 **`export`**，或在 **`docker-compose.yml`** 的 **`panel.environment`** 里自行追加条目。未设置 **`V2RAY_DOCKER_CONTAINER`** 时，面板「重启 V2Ray」会按 Compose 标签自动查找 **`v2ray`** 服务。

面板进程读取：`V2RAY_CONFIG_PATH`（默认 `/v2ray/config.json`）。Compose 已为 **panel** 挂载 **`/var/run/docker.sock`**，便于在后台一键 **`docker restart`** 重启 **v2ray**（等同在宿主机执行；请确保面板账号密码强度足够，避免泄露 Docker 控制权）。

### 流量统计说明（按月）

- 面板内 **单独线程** 按 **`TRAFFIC_POLL_INTERVAL_SEC`**（默认 **3600 秒**）调用 **StatsService.QueryStats**，且 **`reset=True`**：读出当前计数器后立即清空 V2Ray 侧计数，读到的字节作为 **增量** 累加到 **`TRAFFIC_STORE_PATH`**（默认 **`/v2ray/panel_traffic_monthly.json`**），按 **`TRAFFIC_MONTH_TZ`**（可选，如 **`Asia/Shanghai`**）划分 **自然月**。
- 列表里展示的是 **本月累计上下行**（读 JSON，**不**在每次打开页面时直连 Stats）。
- **panel / v2ray / 宿主机重启**：只要 **`./v2ray` 挂载目录不删**，历史月份与本月累计 **不会丢**；V2Ray 重启只会丢掉「尚未被下一轮采集读走」的进程内计数，下一采集周期会继续累加增量。

## 本地开发（可选）

```bash
cd web && pip install -r requirements.txt
export V2RAY_CONFIG_PATH="$(pwd)/../v2ray/config.json"
export TRAFFIC_STORE_PATH="$(pwd)/../v2ray/panel_traffic_monthly.json"
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

管理路由仍需结合 Caddy Basic Auth；直连调试时可暂时注释 Caddy 中的 `basicauth` 块（不推荐在生产环境）。

## 仓库布局

- `web/`：FastAPI 应用与 Dockerfile  
- `caddy/`：`Caddyfile`  
- `v2ray/`：`config.json`（运行时挂载）
- `web/sneat-1.0.0/assets/`：Sneat 主题 CSS/JS（管理页 `/assets/*`）
