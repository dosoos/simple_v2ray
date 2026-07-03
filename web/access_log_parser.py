"""解析 V2Ray access log，按目标域名 / IP 累计连接次数。"""

from __future__ import annotations

import os
import re
from pathlib import Path

# 例：2023/07/04 12:00:00 tcp:192.168.1.1:54321 accepted tcp:example.com:443 [direct]
_ACCEPTED_DEST_RE = re.compile(
    r"accepted\s+(?:tcp|udp):([^:\s]+):\d+",
    re.IGNORECASE,
)
_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def default_access_log_path() -> Path:
    return Path(os.environ.get("V2RAY_ACCESS_LOG_PATH", "/v2ray/access.log")).resolve()


def parse_access_log_delta(path: Path, offset: int) -> tuple[dict[str, int], dict[str, int], int]:
    """
    从 offset 起读取新增日志行，返回 (domains, ips, new_offset)。
    值为连接次数增量。
    """
    domains: dict[str, int] = {}
    ips: dict[str, int] = {}
    if not path.is_file():
        return domains, ips, offset

    size = path.stat().st_size
    if offset > size:
        offset = 0

    with path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        for line in f:
            m = _ACCEPTED_DEST_RE.search(line)
            if not m:
                continue
            host = m.group(1).lower().rstrip(".")
            if not host:
                continue
            if host.startswith("www."):
                host = host[4:]
            if _IP_RE.match(host):
                ips[host] = ips.get(host, 0) + 1
            else:
                domains[host] = domains.get(host, 0) + 1
        new_offset = f.tell()

    return domains, ips, new_offset
