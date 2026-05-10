"""解析 / 修改 V2Ray config.json 中的 VMess 入站 clients。"""

from __future__ import annotations

import copy
import uuid
from typing import Any


def load_config(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("配置根对象必须是 JSON 对象")
    return data


def find_vmess_inbound(config: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    inbounds = config.get("inbounds")
    if not isinstance(inbounds, list):
        raise ValueError("配置缺少 inbounds 数组")
    for i, ib in enumerate(inbounds):
        if isinstance(ib, dict) and ib.get("protocol") == "vmess":
            return i, ib
    raise ValueError("未找到 protocol 为 vmess 的入站，请检查 config.json")


def list_clients(config: dict[str, Any]) -> list[dict[str, Any]]:
    _, inbound = find_vmess_inbound(config)
    settings = inbound.setdefault("settings", {})
    raw = settings.get("clients")
    if not isinstance(raw, list):
        raw = []
        settings["clients"] = raw
    out: list[dict[str, Any]] = []
    for i, c in enumerate(raw):
        if not isinstance(c, dict):
            continue
        out.append(
            {
                "index": i,
                "id": str(c.get("id", "")),
                "email": str(c.get("email", "")),
            }
        )
    return out


def _normalize_client(body: dict[str, Any]) -> dict[str, Any]:
    email = str(body.get("email", "")).strip()
    if not email:
        raise ValueError("备注(email) 不能为空")
    cid = str(body.get("id", "")).strip()
    if cid:
        try:
            uuid.UUID(cid)
        except ValueError as e:
            raise ValueError("UUID 格式无效") from e
    else:
        cid = str(uuid.uuid4())
    # 面板固定为 VMess 默认：alterId / level 恒为 0
    return {"id": cid, "email": email, "alterId": 0, "level": 0}


def add_client(config: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    _, inbound = find_vmess_inbound(config)
    settings = inbound.setdefault("settings", {})
    clients = settings.setdefault("clients", [])
    if not isinstance(clients, list):
        raise ValueError("clients 必须是数组")
    c = _normalize_client(body)
    for ex in clients:
        if isinstance(ex, dict) and str(ex.get("email", "")).strip() == c["email"]:
            raise ValueError("该备注(email) 已存在")
    clients.append(c)
    return c


def update_client(config: dict[str, Any], index: int, body: dict[str, Any]) -> dict[str, Any]:
    _, inbound = find_vmess_inbound(config)
    settings = inbound.setdefault("settings", {})
    clients = settings.get("clients")
    if not isinstance(clients, list) or index < 0 or index >= len(clients):
        raise IndexError("客户端索引无效")
    old = clients[index]
    if not isinstance(old, dict):
        old = {}
    merged = {**old, **body}
    c = _normalize_client(merged)
    for i, ex in enumerate(clients):
        if i != index and isinstance(ex, dict) and str(ex.get("email", "")).strip() == c["email"]:
            raise ValueError("该备注(email) 已被其他用户使用")
    clients[index] = c
    return c


def delete_client(config: dict[str, Any], index: int) -> None:
    _, inbound = find_vmess_inbound(config)
    settings = inbound.setdefault("settings", {})
    clients = settings.get("clients")
    if not isinstance(clients, list) or index < 0 or index >= len(clients):
        raise IndexError("客户端索引无效")
    clients.pop(index)


def merge_vmess_clients(
    base: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    """将 incoming 中 vmess 的 clients 按 email 合并进 base（同 email 覆盖，新 email 追加）。"""
    out = copy.deepcopy(base)
    try:
        _, ib_in = find_vmess_inbound(incoming)
    except ValueError:
        return out
    incoming_clients = ib_in.get("settings", {}).get("clients")
    if not isinstance(incoming_clients, list) or not incoming_clients:
        return out

    _, ib_out = find_vmess_inbound(out)
    settings = ib_out.setdefault("settings", {})
    cur = settings.setdefault("clients", [])
    if not isinstance(cur, list):
        cur = []
        settings["clients"] = cur

    by_email: dict[str, dict[str, Any]] = {}
    for c in cur:
        if isinstance(c, dict) and c.get("email"):
            by_email[str(c["email"])] = c

    for c in incoming_clients:
        if not isinstance(c, dict):
            continue
        try:
            norm = _normalize_client(
                {
                    "email": c.get("email"),
                    "id": c.get("id"),
                }
            )
        except ValueError:
            continue
        em = norm["email"]
        if em in by_email:
            by_email[em].update(norm)
        else:
            cur.append(norm)
            by_email[em] = cur[-1]

    return out
