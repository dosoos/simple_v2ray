"""根据 VMess 入站与用户生成对外分享链接（vmess / Clash YAML / V2Ray JSON）。"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from v2ray_config import find_vmess_inbound, list_clients


def _env_bool(key: str, default: bool) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _primary_connect_host(raw: str) -> str:
    """多域名（逗号/分号/中文逗号分隔）时取第一个，作为客户端连接地址与分享链接。"""
    s = raw.strip()
    if not s:
        return "localhost"
    for sep in ("，", ";", ","):
        s = s.replace(sep, ",")
    first = s.split(",")[0].strip()
    return first if first else "localhost"


def public_endpoint(public_host: str | None = None) -> tuple[str, int, bool]:
    """用户客户端应连接的对端地址；优先使用调用方传入的当前访问域名。"""
    raw = (
        (public_host or "").strip()
        or os.environ.get("PUBLIC_PROXY_HOST", "").strip()
        or ""
    )
    host = _primary_connect_host(raw) if raw else "localhost"
    port_s = os.environ.get("PUBLIC_PROXY_PORT", "").strip()
    tls_default = host not in ("localhost", "127.0.0.1")
    tls = _env_bool("PUBLIC_PROXY_TLS", tls_default)
    if port_s:
        port = int(port_s)
    else:
        port = 443 if tls else 80
    return host, port, tls


def inbound_stream_meta(inbound: dict[str, Any]) -> dict[str, Any]:
    ss = inbound.get("streamSettings") or {}
    net = ss.get("network") or "tcp"
    out: dict[str, Any] = {"network": net}
    if net == "ws":
        ws = ss.get("wsSettings") or {}
        out["ws_path"] = str(ws.get("path") or "/")
        h = (ws.get("headers") or {}).get("Host")
        out["ws_host"] = str(h).strip() if h else ""
    else:
        out["ws_path"] = ""
        out["ws_host"] = ""
    return out


def _yaml_escape_name(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_vmess_uri(
    *,
    remark: str,
    uuid_str: str,
    host: str,
    port: int,
    alter_id: int,
    network: str,
    ws_path: str,
    ws_host: str,
    tls: bool,
) -> str:
    path = ws_path if network == "ws" else ""
    header_host = (ws_host or host) if network == "ws" else ""
    obj: dict[str, Any] = {
        "v": "2",
        "ps": remark,
        "add": host,
        "port": str(port),
        "id": uuid_str,
        "aid": str(alter_id),
        "scy": "auto",
        "net": network,
        "type": "none",
        "host": header_host,
        "path": path,
        "tls": "tls" if tls else "",
    }
    if tls:
        obj["sni"] = host
        obj["alpn"] = ""
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "vmess://" + base64.b64encode(raw).decode("ascii")


def build_clash_vmess_yaml(
    *,
    remark: str,
    uuid_str: str,
    host: str,
    port: int,
    alter_id: int,
    network: str,
    ws_path: str,
    ws_host: str,
    tls: bool,
) -> str:
    name = _yaml_escape_name((remark or "vmess")[:80])
    lines = [
        "proxies:",
        f'  - name: "{name}"',
        "    type: vmess",
        f"    server: {host}",
        f"    port: {port}",
        f"    uuid: {uuid_str}",
        f"    alterId: {alter_id}",
        "    cipher: auto",
        f"    tls: {str(tls).lower()}",
    ]
    if tls:
        lines.append(f"    servername: {host}")
        lines.append("    skip-cert-verify: false")
    if network == "ws":
        hh = ws_host or host
        lines.append("    network: ws")
        lines.append("    ws-opts:")
        lines.append(f"      path: {ws_path}")
        lines.append("      headers:")
        lines.append(f'        Host: "{hh}"')
    else:
        lines.append("    network: tcp")
    return "\n".join(lines)


def build_v2ray_outbound_json(
    *,
    uuid_str: str,
    host: str,
    port: int,
    alter_id: int,
    network: str,
    ws_path: str,
    ws_host: str,
    tls: bool,
) -> str:
    stream: dict[str, Any] = {"network": network}
    if tls:
        stream["security"] = "tls"
        stream["tlsSettings"] = {
            "serverName": host,
            "allowInsecure": False,
        }
    else:
        stream["security"] = "none"
    if network == "ws":
        stream["wsSettings"] = {
            "path": ws_path,
            "headers": {"Host": ws_host or host},
        }
    outbound = {
        "protocol": "vmess",
        "settings": {
            "vnext": [
                {
                    "address": host,
                    "port": port,
                    "users": [
                        {
                            "id": uuid_str,
                            "alterId": alter_id,
                            "security": "auto",
                        }
                    ],
                }
            ]
        },
        "streamSettings": stream,
        "tag": "proxy",
    }
    return json.dumps(outbound, ensure_ascii=False, indent=2) + "\n"


def build_share_payload(
    config: dict[str, Any], index: int, public_host: str | None = None
) -> dict[str, Any]:
    clients = list_clients(config)
    if index < 0 or index >= len(clients):
        raise IndexError("客户端索引无效")
    _, inbound = find_vmess_inbound(config)
    raw_list = inbound.get("settings", {}).get("clients")
    if not isinstance(raw_list, list) or index >= len(raw_list):
        raise IndexError("客户端索引无效")
    raw = raw_list[index]
    if not isinstance(raw, dict):
        raise ValueError("客户端数据无效")

    email = str(raw.get("email", ""))
    uuid_str = str(raw.get("id", ""))
    alter_id = int(raw.get("alterId", 0) or 0)

    host, pub_port, tls = public_endpoint(public_host)
    sm = inbound_stream_meta(inbound)
    net = sm["network"]

    # 分享链接中的「备注 / 节点名」使用对外域名，不用面板里的用户备注（email）
    node_label = host or "vmess"

    vmess_uri = build_vmess_uri(
        remark=node_label,
        uuid_str=uuid_str,
        host=host,
        port=pub_port,
        alter_id=alter_id,
        network=net,
        ws_path=str(sm.get("ws_path") or ""),
        ws_host=str(sm.get("ws_host") or ""),
        tls=tls,
    )
    clash_yaml = build_clash_vmess_yaml(
        remark=node_label,
        uuid_str=uuid_str,
        host=host,
        port=pub_port,
        alter_id=alter_id,
        network=net,
        ws_path=str(sm.get("ws_path") or ""),
        ws_host=str(sm.get("ws_host") or ""),
        tls=tls,
    )
    v2ray_out = build_v2ray_outbound_json(
        uuid_str=uuid_str,
        host=host,
        port=pub_port,
        alter_id=alter_id,
        network=net,
        ws_path=str(sm.get("ws_path") or ""),
        ws_host=str(sm.get("ws_host") or ""),
        tls=tls,
    )

    hint: str | None = None
    if host in ("localhost", "127.0.0.1"):
        hint = "当前对外地址为 localhost，请运行 ./scripts/init 配置实际域名后再分享给用户。"

    return {
        "email": email,
        "uuid": uuid_str,
        "share_node_label": node_label,
        "public_host": host,
        "public_port": pub_port,
        "public_tls": tls,
        "network": net,
        "vmess_uri": vmess_uri,
        "clash_yaml": clash_yaml,
        "v2ray_outbound_json": v2ray_out,
        "host_hint": hint,
    }
