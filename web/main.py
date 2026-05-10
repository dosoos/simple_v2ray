"""单节点 V2Ray 配置面板：直接读写 config.json，无数据库。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles as StarletteStaticFiles

from traffic_poller import start_traffic_poller_thread
from traffic_store import get_store
from share_links import build_share_payload
from v2ray_stats import enrich_clients_traffic
from v2ray_config import (
    add_client,
    delete_client,
    find_vmess_inbound,
    list_clients,
    load_config,
    merge_vmess_clients,
    update_client,
)

CONFIG_PATH = Path(os.environ.get("V2RAY_CONFIG_PATH", "/v2ray/config.json")).resolve()

DOCKER_SOCK = Path(os.environ.get("DOCKER_SOCKET_PATH", "/var/run/docker.sock"))

# Sneat 主题静态资源（与 `sneat-1.0.0/html` 中 `../assets/` 一致）
ASSETS_DIR = Path(__file__).parent / "sneat-1.0.0" / "assets"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    get_store().load()
    start_traffic_poller_thread()
    logging.getLogger("uvicorn.error").info("流量采集线程已启动（按 TRAFFIC_POLL_INTERVAL_SEC 周期，reset 增量写入本月）")
    yield


app = FastAPI(title="VPC Panel", docs_url=None, redoc_url=None, lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

if ASSETS_DIR.is_dir():
    app.mount("/assets", StarletteStaticFiles(directory=str(ASSETS_DIR)), name="assets")


def _read_config_raw() -> str:
    if not CONFIG_PATH.is_file():
        return "{}\n"
    return CONFIG_PATH.read_text(encoding="utf-8")


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 无效: {e}") from e


def _load_config_dict() -> dict[str, Any]:
    raw = _read_config_raw()
    data = _parse_json(raw)
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="配置根必须是 JSON 对象")
    return load_config(data)


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _save_config_dict(data: dict[str, Any]) -> None:
    _atomic_write_json(CONFIG_PATH, data)


def _vmess_meta(config: dict[str, Any]) -> dict[str, Any]:
    _, ib = find_vmess_inbound(config)
    ss = ib.get("streamSettings") or {}
    ws = ss.get("wsSettings") or {}
    return {
        "port": ib.get("port"),
        "listen": ib.get("listen"),
        "ws_path": ws.get("path"),
        "network": ss.get("network"),
    }


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "VPC proxy — 管理入口：/panel/（由 Caddy Basic Auth 保护）"


@app.get("/panel/", response_class=HTMLResponse)
@app.get("/panel", response_class=HTMLResponse)
def panel_ui(request: Request) -> HTMLResponse:
    clients: list[dict[str, Any]] = []
    load_error: str | None = None
    traffic_error: str | None = None
    try:
        cfg = _load_config_dict()
        clients = list_clients(cfg)
        clients, traffic_error = enrich_clients_traffic(clients)
    except HTTPException as e:
        d = e.detail
        load_error = d if isinstance(d, str) else str(d)
    except ValueError as e:
        load_error = str(e)

    return templates.TemplateResponse(
        request=request,
        name="panel.html",
        context={
            "clients": clients,
            "config_path": str(CONFIG_PATH),
            "load_error": load_error,
            "traffic_error": traffic_error,
            "traffic_month": get_store().current_month_label(),
            "admin_user": os.environ.get("CADDY_ADMIN_USER", "admin"),
        },
    )


@app.get("/api/panel/clients")
def api_list_clients() -> JSONResponse:
    cfg = _load_config_dict()
    clients, traffic_error = enrich_clients_traffic(list_clients(cfg))
    return JSONResponse(
        content={
            "clients": clients,
            "vmess": _vmess_meta(cfg),
            "traffic_error": traffic_error,
            "traffic_month": get_store().current_month_label(),
        }
    )


@app.get("/api/panel/clients/{index:int}/share")
def api_client_share(index: int) -> JSONResponse:
    cfg = _load_config_dict()
    try:
        return JSONResponse(content=build_share_payload(cfg, index))
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/api/panel/clients")
async def api_add_client(request: Request) -> JSONResponse:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体须为 JSON 对象")
    cfg = _load_config_dict()
    try:
        add_client(cfg, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _save_config_dict(cfg)
    return JSONResponse(content={"ok": True})


@app.patch("/api/panel/clients/{index:int}")
async def api_patch_client(index: int, request: Request) -> JSONResponse:
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="请求体须为 JSON 对象")
    cfg = _load_config_dict()
    try:
        update_client(cfg, index, body)
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _save_config_dict(cfg)
    return JSONResponse(content={"ok": True})


@app.delete("/api/panel/clients/{index:int}")
def api_del_client(index: int) -> JSONResponse:
    cfg = _load_config_dict()
    try:
        delete_client(cfg, index)
    except IndexError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _save_config_dict(cfg)
    return JSONResponse(content={"ok": True})


@app.get("/api/panel/export")
def api_export_file() -> FileResponse:
    if not CONFIG_PATH.is_file():
        raise HTTPException(status_code=404, detail="配置文件不存在")
    return FileResponse(
        CONFIG_PATH,
        filename="config.json",
        media_type="application/json",
    )


@app.get("/api/panel/config")
def api_get_config() -> JSONResponse:
    raw = _read_config_raw()
    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        body = None
    return JSONResponse(content={"path": str(CONFIG_PATH), "raw": raw, "json": body})


@app.put("/api/panel/config")
async def api_put_config(request: Request) -> JSONResponse:
    text = (await request.body()).decode("utf-8")
    data = _parse_json(text)
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="根对象须为 JSON 对象")
    _save_config_dict(data)
    return JSONResponse(content={"ok": True, "path": str(CONFIG_PATH)})


@app.post("/api/panel/import")
async def api_import(
    file: UploadFile = File(...),
    overwrite: str = Form("0"),
) -> JSONResponse:
    body = await file.read()
    text = body.decode("utf-8")
    incoming = _parse_json(text)
    if not isinstance(incoming, dict):
        raise HTTPException(status_code=400, detail="须上传 JSON 对象")

    if overwrite.lower() in ("1", "true", "yes", "on"):
        _save_config_dict(incoming)
        return JSONResponse(content={"ok": True, "mode": "full_replace"})

    base = _load_config_dict()
    try:
        merged = merge_vmess_clients(base, incoming)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    _save_config_dict(merged)
    return JSONResponse(content={"ok": True, "mode": "merge_clients"})


def _restart_v2ray_via_docker() -> dict[str, Any]:
    """通过宿主机 Docker（需挂载 /var/run/docker.sock）重启 v2ray 容器。"""
    if not DOCKER_SOCK.exists():
        raise HTTPException(
            status_code=503,
            detail="未挂载 Docker socket：请在 compose 的 panel 服务中添加 volumes: /var/run/docker.sock:/var/run/docker.sock",
        )
    if not shutil.which("docker"):
        raise HTTPException(status_code=503, detail="镜像内缺少 docker 命令（构建异常）")

    explicit = os.environ.get("V2RAY_DOCKER_CONTAINER", "").strip()
    if explicit:
        target = explicit
    else:
        proc = subprocess.run(
            ["docker", "ps", "-q", "-f", "label=com.docker.compose.service=v2ray"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"docker ps 失败: {(proc.stderr or proc.stdout or '').strip()}",
            )
        ids = [x for x in proc.stdout.strip().split("\n") if x]
        if not ids:
            raise HTTPException(
                status_code=404,
                detail="未找到 Compose 服务名为 v2ray 的容器。请设置环境变量 V2RAY_DOCKER_CONTAINER 为容器名或短 ID（docker ps）",
            )
        target = ids[0]

    proc = subprocess.run(
        ["docker", "restart", target],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip() or "docker restart 失败"
        raise HTTPException(status_code=500, detail=msg)
    return {"ok": True, "target": target}


@app.post("/api/panel/restart-v2ray")
def api_restart_v2ray() -> JSONResponse:
    result = _restart_v2ray_via_docker()
    return JSONResponse(content=result)
