## 架构（单节点简化版）

```
客户端 ──HTTPS/WSS──► Caddy ──/proxy──► V2Ray (VMess)
                         │
                         └──/panel*, /api/panel*, /assets/* (Basic Auth)──► FastAPI
```

- **无数据库**：面板只读写挂载卷中的 `v2ray/config.json`（导入/导出亦围绕该文件）。
- **认证边界**：管理路径由 **Caddy `basicauth`** 拦截；面板应用信任内网反代，不再单独登录。
- **配置生效**：写入 JSON 后通常需 **`docker compose restart v2ray`**（视 V2Ray 是否监听文件变更而定，当前镜像一般为静态加载）。
- **流量统计**：后台线程按间隔调用 **StatsService.QueryStats(reset=true)** 取增量，累加到挂载卷上的 **`panel_traffic_monthly.json`**，按 **自然月** 汇总展示；panel/V2Ray 容器重启不丢已写入文件的数据。
