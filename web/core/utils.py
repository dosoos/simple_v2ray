import base64
import json
from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone

from core.models import ProxyUser, TrafficSnapshot
from core import config


def build_vmess_share_link(user: ProxyUser) -> str:
    host = config.HOST_DOMAIN.split(",")[0].strip()
    port = config.V2RAY_PUBLIC_PORT
    net = "ws"
    path = config.V2RAY_WS_PATH
    tls = "tls" if config.V2RAY_PUBLIC_PORT == 443 else "none"
    payload = {
        "v": "2",
        "ps": user.label,
        "add": host,
        "port": str(port),
        "id": str(user.uuid),
        "aid": str(user.alter_id),
        "net": net,
        "type": "none",
        "host": "",
        "path": path,
        "tls": tls,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    b64 = base64.b64encode(raw.encode("utf-8")).decode("ascii")
    return f"vmess://{b64}"


def build_v2ray_config_dict(users: list[ProxyUser]) -> dict[str, Any]:
    clients = []
    for u in users:
        if not u.enabled:
            continue
        clients.append(
            {
                "id": str(u.uuid).upper(),
                "level": u.level,
                "alterId": u.alter_id,
                "email": u.label,
            }
        )
    if not clients:
        clients.append(
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "level": 0,
                "alterId": 0,
                "email": "placeholder-disabled",
            }
        )

    return {
        "stats": {},
        "api": {
            "tag": "api",
            "services": ["StatsService"],
        },
        "policy": {
            "levels": {
                "0": {
                    "statsUserUplink": True,
                    "statsUserDownlink": True,
                }
            },
            "system": {
                "statsInboundUplink": True,
                "statsInboundDownlink": True,
                "statsOutboundUplink": True,
                "statsOutboundDownlink": True,
            },
        },
        "inbounds": [
            {
                "port": config.V2RAY_VMESS_PORT,
                "listen": "0.0.0.0",
                "protocol": "vmess",
                "settings": {"clients": clients},
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {"path": config.V2RAY_WS_PATH},
                },
            },
            {
                "listen": "0.0.0.0",
                "port": config.V2RAY_API_PORT,
                "protocol": "dokodemo-door",
                "settings": {"address": "127.0.0.1"},
                "tag": "api",
            },
        ],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom", "settings": {}},
            {"tag": "api", "protocol": "freedom", "settings": {}},
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "strategy": "rules",
            "rules": [
                {"type": "field", "inboundTag": ["api"], "outboundTag": "api"}
            ],
        },
    }


def aggregate_traffic_for_user(
    user: ProxyUser,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, int]:
    """用相邻快照差值估算区间流量；区间为 [start, end]。"""
    now = timezone.now()
    if end is None:
        end = now
    if start is None:
        start = end - timedelta(hours=24)

    qs = TrafficSnapshot.objects.filter(user=user, recorded_at__lte=end).order_by(
        "recorded_at"
    )
    before = qs.filter(recorded_at__lt=start).last()
    in_range = list(qs.filter(recorded_at__gte=start, recorded_at__lte=end))
    if not in_range:
        return {"uplink_delta": 0, "downlink_delta": 0, "samples": 0}

    first = before or in_range[0]
    last = in_range[-1]

    return {
        "uplink_delta": max(0, last.uplink_bytes - first.uplink_bytes),
        "downlink_delta": max(0, last.downlink_bytes - first.downlink_bytes),
        "samples": len(in_range),
    }

