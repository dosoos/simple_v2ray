# 个人简易多节点VPN代理系统

## 项目介绍

当前项目是一个轻量化的vpn翻墙代理管理系统，翻墙服务基于v2fly开源项目，
支持多用户管理，用户流量概览，以便在多个vps上可以快速搭建起节点，
管理页面采用template配合caddy做后台登录认证，fastapi直接管理v2ray中的config.json,
前端使用caddy做https加密反向代理，集合本系统做管理。

### 方向细化

- **后台**：Caddy + FastAPI 管理用户、 二维码， 订阅连接等。
- **代理**：V2Ray 承载 VMess/VLESS 等入站。
- **入口**：Caddy 统一 TLS 与 WebSocket 路径反代，与 V2Ray `streamSettings` 对齐。

## 文档

更完整的架构与流程说明已整理到 `docs/`：


## 功能列表

- 用户管理，增删改查，订阅连接, 流量使用情况等
- 配置导入导出，可选覆盖导入， 方便节点数据迁移。


## 项目部署

项目使用 Docker Compose 一键启动：`app`（FastAPI）、`caddy`（HTTPS 与 WebSocket 反代）、`v2ray`（VMess 入站）。

### 快速开始

1. 配置文件：`cp .env.example .env`，填写 `ADMIN_USERNAME`、`ADMIN_PASSWORD`、`HOST_DOMAIN`。
2. 启动：`docker compose up -d --build`。

### 环境变量说明

`.env.example` 仅保留必要变量（`HOST_DOMAIN`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`）。

| 变量 | 含义 |
| --- | --- |
| `HOST_DOMAIN` | Caddy 站点名与 TLS 证书域名；也用于生成订阅链接中的地址 |
| `ADMIN_USERNAME` | 管理后台登录账号 |
| `ADMIN_PASSWORD` | 管理后台登录密码 |

