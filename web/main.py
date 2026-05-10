"""单节点 V2Ray 配置面板：直接读写 config.json，无数据库。"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

CONFIG_PATH = Path(os.environ.get("V2RAY_CONFIG_PATH", "/v2ray/config.json")).resolve()
BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/v2ray/backups")).resolve()

BACKUP_NAME_RE = re.compile(r"^config-backup-\d{8}-\d{6}\.json$")

app = FastAPI(title="VPC Panel", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _ensure_dirs() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _read_config_raw() -> str:
    if not CONFIG_PATH.is_file():
        return "{}\n"
    return CONFIG_PATH.read_text(encoding="utf-8")


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 无效: {e}") from e


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


@app.on_event("startup")
def _startup() -> None:
    _ensure_dirs()


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "VPC proxy — 管理入口：/panel/（由 Caddy Basic Auth 保护）"


@app.get("/panel/", response_class=HTMLResponse)
@app.get("/panel", response_class=HTMLResponse)
def panel_ui(request: Request) -> HTMLResponse:
    raw = _read_config_raw()
    backups = list_backups_internal()
    return templates.TemplateResponse(
        "panel.html",
        {
            "request": request,
            "config_text": raw,
            "backups": backups,
            "config_path": str(CONFIG_PATH),
            "backup_dir": str(BACKUP_DIR),
        },
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
    _atomic_write_json(CONFIG_PATH, data)
    return JSONResponse(content={"ok": True, "path": str(CONFIG_PATH)})


def list_backups_internal() -> list[str]:
    _ensure_dirs()
    names: list[str] = []
    for p in sorted(BACKUP_DIR.glob("config-backup-*.json"), reverse=True):
        if p.is_file() and BACKUP_NAME_RE.match(p.name):
            names.append(p.name)
    return names


@app.get("/api/panel/backups")
def api_list_backups() -> JSONResponse:
    return JSONResponse(content={"backups": list_backups_internal()})


@app.post("/api/panel/backups")
def api_create_backup() -> JSONResponse:
    _ensure_dirs()
    raw = _read_config_raw()
    _parse_json(raw)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = f"config-backup-{ts}.json"
    dest = BACKUP_DIR / name
    shutil.copy2(CONFIG_PATH, dest) if CONFIG_PATH.is_file() else dest.write_text(
        raw, encoding="utf-8"
    )
    return JSONResponse(content={"ok": True, "file": name})


@app.get("/api/panel/backups/{filename}")
def api_download_backup(filename: str) -> FileResponse:
    if not BACKUP_NAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    path = (BACKUP_DIR / filename).resolve()
    if not str(path).startswith(str(BACKUP_DIR.resolve())) or not path.is_file():
        raise HTTPException(status_code=404, detail="备份不存在")
    return FileResponse(
        path,
        filename=filename,
        media_type="application/json",
    )


@app.post("/api/panel/import")
async def api_import(file: UploadFile = File(...)) -> JSONResponse:
    body = await file.read()
    text = body.decode("utf-8")
    data = _parse_json(text)
    _atomic_write_json(CONFIG_PATH, data)
    return JSONResponse(content={"ok": True, "path": str(CONFIG_PATH)})


@app.post("/api/panel/restore/{filename}")
def api_restore_backup(filename: str) -> JSONResponse:
    if not BACKUP_NAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    src = (BACKUP_DIR / filename).resolve()
    if not str(src).startswith(str(BACKUP_DIR.resolve())) or not src.is_file():
        raise HTTPException(status_code=404, detail="备份不存在")
    text = src.read_text(encoding="utf-8")
    data = _parse_json(text)
    _atomic_write_json(CONFIG_PATH, data)
    return JSONResponse(content={"ok": True, "restored_from": filename})
