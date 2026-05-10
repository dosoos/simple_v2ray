import os


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


# === 仅保留必要的 env ===
HOST_DOMAIN = _env("HOST_DOMAIN", "localhost")
MASTER_URL = _env("MASTER_URL", "").rstrip("/")


# === 节点角色：默认主节点；配置了 MASTER_URL 即视为从节点 ===
NODE_ROLE = "slave" if MASTER_URL else "master"
# 本机节点显示名称（与 token UUID 共同标识节点；多机部署时请为每台设置不同名称便于区分）
NODE_NAME = _env("NODE_NAME", "node-1")


# === V2Ray 固定参数（避免堆环境变量） ===
V2RAY_WS_PATH = "/proxy"
V2RAY_PUBLIC_PORT = 443
V2RAY_INTERNAL_HOST = "v2ray"
V2RAY_VMESS_PORT = 58888
V2RAY_API_HOST = "v2ray"
V2RAY_API_PORT = 10085


# === 文件路径（Compose 卷挂载） ===
DATABASE_PATH = "/data/db.sqlite3"
V2RAY_EXPORT_PATH = "/v2ray/config.json"

