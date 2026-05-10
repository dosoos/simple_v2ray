"""后台线程：定时向 V2Ray QueryStats(reset=True) 取增量并写入 traffic_store。"""

from __future__ import annotations

import logging
import os
import threading
import time

from traffic_store import get_store
from v2ray_stats import query_user_traffic

log = logging.getLogger("vpc.traffic_poller")


def _poll_once() -> None:
    store = get_store()
    raw, err = query_user_traffic(reset=True)
    if err:
        store.set_last_poll_error(err)
        log.warning("Stats 查询失败: %s", err)
        return
    store.set_last_poll_error(None)
    if raw:
        store.add_delta(raw)
        log.debug("已写入流量增量: %d 个用户计数器", len(raw))


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
