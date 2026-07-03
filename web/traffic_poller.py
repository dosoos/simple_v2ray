"""后台线程：定时向 V2Ray QueryStats(reset=True) 取增量并写入 traffic_store。"""

from __future__ import annotations

import logging
import os
import threading
import time

from access_log_parser import default_access_log_path, parse_access_log_delta
from traffic_store import get_store
from v2ray_stats import query_stats

log = logging.getLogger("vpc.traffic_poller")


def _poll_access_log() -> None:
    store = get_store()
    path = default_access_log_path()
    offset = store.get_access_log_offset()
    domains, ips, new_offset = parse_access_log_delta(path, offset)
    if new_offset != offset:
        store.set_access_log_offset(new_offset)
    if domains or ips:
        store.add_access_delta(domains, ips)
        log.debug(
            "access log 增量: %d 域名项, %d IP 项",
            len(domains),
            len(ips),
        )


def _poll_once() -> None:
    store = get_store()
    users, outbounds, err = query_stats(reset=True)
    if err:
        store.set_last_poll_error(err)
        log.warning("Stats 查询失败: %s", err)
        return
    store.set_last_poll_error(None)
    if users:
        store.add_user_delta(users)
        log.debug("已写入用户流量增量: %d 个计数器", len(users))
    if outbounds:
        store.add_outbound_delta(outbounds)
        log.debug("已写入出站流量增量: %d 个计数器", len(outbounds))
    try:
        _poll_access_log()
    except Exception:
        log.exception("access log 解析失败")


def traffic_poll_loop() -> None:
    initial = max(0, int(os.environ.get("TRAFFIC_POLL_INITIAL_DELAY_SEC", "15")))
    interval = max(60, int(os.environ.get("TRAFFIC_POLL_INTERVAL_SEC", "3600")))
    time.sleep(initial)
    while True:
        try:
            _poll_once()
        except Exception:
            log.exception("流量采集异常")
            try:
                get_store().set_last_poll_error("采集线程异常，详见日志")
            except Exception:
                pass
        time.sleep(interval)


def start_traffic_poller_thread() -> threading.Thread:
    t = threading.Thread(target=traffic_poll_loop, name="traffic-poller", daemon=True)
    t.start()
    return t
