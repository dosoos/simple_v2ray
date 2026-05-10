"""按月累计流量持久化（挂载卷 JSON），与 V2Ray 进程生命周期解耦。"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


def _month_key() -> str:
    tz = os.environ.get("TRAFFIC_MONTH_TZ", "").strip()
    if tz:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo(tz)).strftime("%Y-%m")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m")


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


class MonthlyTrafficStore:
    """存储结构：{ \"version\": 1, \"months\": { \"YYYY-MM\": { \"email\": { \"up\", \"down\" } } } }"""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {"version": 1, "months": {}}
        self._last_poll_error: str | None = None

    def load(self) -> None:
        with self._lock:
            if self.path.is_file():
                try:
                    raw = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict) and isinstance(raw.get("months"), dict):
                        self._data["months"] = raw["months"]
                        self._data["version"] = raw.get("version", 1)
                except (json.JSONDecodeError, OSError):
                    pass

    def set_last_poll_error(self, msg: str | None) -> None:
        with self._lock:
            self._last_poll_error = msg

    def get_last_poll_error(self) -> str | None:
        with self._lock:
            return self._last_poll_error

    def current_month_label(self) -> str:
        return _month_key()

    def add_delta(self, deltas: dict[str, dict[str, int]]) -> None:
        """将本轮 QueryStats(reset=True) 得到的增量累计进当前自然月桶。"""
        if not deltas:
            return
        mk = _month_key()
        with self._lock:
            months: dict[str, Any] = self._data.setdefault("months", {})
            bucket = months.setdefault(mk, {})
            for email, t in deltas.items():
                em = str(email)
                slot = bucket.setdefault(em, {"up": 0, "down": 0})
                slot["up"] = int(slot.get("up", 0)) + int(t.get("uplink", 0))
                slot["down"] = int(slot.get("down", 0)) + int(t.get("downlink", 0))
            _atomic_write_json(self.path, self._data)

    def get_totals_for_emails(self, emails: list[str]) -> tuple[dict[str, dict[str, int]], str | None]:
        """当前月、指定 email 的累计上下行字节。"""
        mk = _month_key()
        with self._lock:
            err = self._last_poll_error
            bucket = self._data.get("months", {}).get(mk, {})
            out: dict[str, dict[str, int]] = {}
            for em in emails:
                s = bucket.get(em, {"up": 0, "down": 0})
                out[em] = {
                    "up": int(s.get("up", 0)),
                    "down": int(s.get("down", 0)),
                }
            return out, err


_store: MonthlyTrafficStore | None = None


def get_store() -> MonthlyTrafficStore:
    global _store
    if _store is None:
        p = Path(os.environ.get("TRAFFIC_STORE_PATH", "/v2ray/panel_traffic_monthly.json")).resolve()
        _store = MonthlyTrafficStore(p)
    return _store
