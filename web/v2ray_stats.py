"""V2Ray StatsService（gRPC）；展示数据来自按月持久化的 traffic_store。"""

from __future__ import annotations

import os
from typing import Any

import grpc

from stats_command_pb2 import QueryStatsRequest
from stats_command_pb2_grpc import StatsServiceStub
from traffic_store import get_store


def format_bytes(n: int) -> str:
    """人类可读字节串（1024 进制）。"""
    if n < 0:
        n = 0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    if i == 0:
        return f"{int(v)} B"
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{s} {units[i]}"


def parse_user_traffic(stats: list[Any]) -> dict[str, dict[str, int]]:
    """将 QueryStats 返回的计数器解析为 email -> uplink/downlink（字节）。"""
    out: dict[str, dict[str, int]] = {}
    for s in stats:
        name = getattr(s, "name", "") or ""
        val = int(getattr(s, "value", 0) or 0)
        parts = name.split(">>>")
        if len(parts) != 4:
            continue
        scope, email, kind, direction = parts
        if scope != "user" or kind != "traffic":
            continue
        slot = out.setdefault(email, {"uplink": 0, "downlink": 0})
        if direction == "uplink":
            slot["uplink"] = val
        elif direction == "downlink":
            slot["downlink"] = val
    return out


def query_user_traffic(
    host: str | None = None,
    port: int | None = None,
    timeout_sec: float = 8.0,
    *,
    reset: bool = False,
) -> tuple[dict[str, dict[str, int]], str | None]:
    """
    调用 StatsService.QueryStats。

    reset=True：读取后立即清零 V2Ray 侧计数器（供定时增量采集）；面板展示不直连此处。
    """
    h = host if host is not None else os.environ.get("V2RAY_API_HOST", "v2ray")
    p = int(port if port is not None else os.environ.get("V2RAY_API_PORT", "10085"))
    addr = f"{h}:{p}"
    channel = grpc.insecure_channel(addr)
    try:
        stub = StatsServiceStub(channel)
        req = QueryStatsRequest(pattern="", reset=reset)
        resp = stub.QueryStats(req, timeout=timeout_sec)
        data = parse_user_traffic(list(resp.stat))
        return data, None
    except grpc.RpcError as e:
        return {}, f"{e.code().name}: {e.details() or 'StatsService 调用失败'}"
    except OSError as e:
        return {}, f"无法连接 Stats API ({addr}): {e}"
    finally:
        channel.close()


def enrich_clients_traffic(clients: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    """附加本月累计（持久化文件）；traffic_error 为最近一次后台采集错误（若有）。"""
    store = get_store()
    emails = [str(c.get("email", "")) for c in clients]
    totals_map, err = store.get_totals_for_emails(emails)
    for c in clients:
        em = str(c.get("email", ""))
        t = totals_map.get(em, {"up": 0, "down": 0})
        up = int(t["up"])
        down = int(t["down"])
        c["bytes_up"] = up
        c["bytes_down"] = down
        c["traffic_up"] = format_bytes(up)
        c["traffic_down"] = format_bytes(down)
    return clients, err
