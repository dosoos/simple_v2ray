from __future__ import annotations

from dataclasses import dataclass

import grpc
from core import config

import v2ray_stats_command_pb2 as pb2
import v2ray_stats_command_pb2_grpc as pb2_grpc


@dataclass(frozen=True)
class V2RayStat:
    name: str
    value: int


def query_stats(pattern: str = "user>>>", reset: bool = False) -> list[V2RayStat]:
    target = f"{config.V2RAY_API_HOST}:{config.V2RAY_API_PORT}"
    channel = grpc.insecure_channel(target)
    stub = pb2_grpc.StatsServiceStub(channel)
    resp: pb2.QueryStatsResponse = stub.QueryStats(
        pb2.QueryStatsRequest(pattern=pattern, reset=reset), timeout=30
    )
    out: list[V2RayStat] = []
    for s in resp.stat:
        out.append(V2RayStat(name=s.name, value=int(s.value)))
    return out


def parse_user_totals(stats: list[V2RayStat]) -> dict[str, tuple[int, int]]:
    """返回 label -> (uplink累计, downlink累计)。"""
    acc: dict[str, dict[str, int]] = {}
    for item in stats:
        name = item.name or ""
        parts = name.split(">>>")
        if len(parts) < 4 or parts[0] != "user":
            continue
        label = parts[1]
        direction = parts[3]
        bucket = acc.setdefault(label, {})
        bucket[direction] = int(item.value)

    out: dict[str, tuple[int, int]] = {}
    for label, dirs in acc.items():
        out[label] = (dirs.get("uplink", 0), dirs.get("downlink", 0))
    return out

