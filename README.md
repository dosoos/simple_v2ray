# 个人简易 VPN 代理（单节点）

Caddy 负责 HTTPS 与反代，V2Ray 提供 VMess，FastAPI 面板管理用户（无数据库，直接读写 `v2ray/config.json`）。

## 快速开始

准备工作: 需要将域名解析到当前 VPS IP，以便 Caddy 可以正常获取 HTTPS 证书。

1. 安装 Docker：`curl https://get.docker.com | sudo bash - && sudo usermod -aG docker $USER`
2. 初始化配置：`chmod +x scripts/init && ./scripts/init`
3. 启动服务：`docker compose up -d --build`
4. 打开管理页：`https://<HOST_DOMAIN>/panel/`

### 修改管理密码

```bash
chmod +x scripts/passwd
./scripts/passwd -p '你的强密码'
docker compose restart caddy
```

## 面板功能

- 表格管理 VMess 用户，支持导出 / 导入配置
- 导入时仅合并 VMess 用户列表，其它字段忽略
- 按月流量统计（数据保存在 `v2ray/panel_traffic_monthly.json`）

## 目录结构

- `web/` — FastAPI 面板
- `caddy/` — Caddy 配置（`Caddyfile` 由 `scripts/init` 生成）
- `v2ray/` — V2Ray 配置（`config.json` 运行时生成，不入库）

详细架构见 `docs/architecture.md`。
