## 架构（单节点简化版）

```
客户端 ──HTTPS/WSS──► Caddy ──/proxy──► V2Ray (VMess)
                         │
                         └──/panel*, /api/panel* (Basic Auth)──► FastAPI
```

- **无数据库**：面板只读写挂载卷中的 `v2ray/config.json` 与 `v2ray/backups/`。
- **认证边界**：管理路径由 **Caddy `basicauth`** 拦截；面板应用信任内网反代，不再单独登录。
- **配置生效**：写入 JSON 后通常需 **`docker compose restart v2ray`**（视 V2Ray 是否监听文件变更而定，当前镜像一般为静态加载）。
