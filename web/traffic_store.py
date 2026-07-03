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


def _empty_month_bucket() -> dict[str, Any]:
    return {"users": {}, "outbounds": {}, "domains": {}, "ips": {}}


def _normalize_month_bucket(bucket: Any) -> dict[str, Any]:
    """兼容 v1（month 下直接是 email -> {up,down}）。"""
    if not isinstance(bucket, dict):
        return _empty_month_bucket()
    if "users" in bucket or "outbounds" in bucket or "domains" in bucket or "ips" in bucket:
        out = _empty_month_bucket()
        for key in out:
            src = bucket.get(key)
            if isinstance(src, dict):
                out[key] = dict(src)
        return out
    return {"users": dict(bucket), "outbounds": {}, "domains": {}, "ips": {}}


class MonthlyTrafficStore:
    """
    存储结构 v2：
    {
      "version": 2,
      "meta": { "access_log_offset": 0 },
      "months": {
        "YYYY-MM": {
          "users": { "email": { "up", "down" } },
          "outbounds": { "tag": { "up", "down" } },
          "domains": { "host": count },
          "ips": { "ip": count }
        }
      }
    }
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {"version": 2, "meta": {"access_log_offset": 0}, "months": {}}
        self._last_poll_error: str | None = None

    def load(self) -> None:
        with self._lock:
            if self.path.is_file():
                try:
                    raw = json.loads(self.path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict) and isinstance(raw.get("months"), dict):
                        self._data["months"] = raw["months"]
                        self._data["version"] = raw.get("version", 2)
                        meta = raw.get("meta")
                        if isinstance(meta, dict):
                            self._data["meta"] = meta
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

    def _current_bucket(self) -> dict[str, Any]:
        months: dict[str, Any] = self._data.setdefault("months", {})
        mk = _month_key()
        bucket = months.get(mk)
        if not isinstance(bucket, dict):
            bucket = _empty_month_bucket()
            months[mk] = bucket
        else:
            bucket = _normalize_month_bucket(bucket)
            months[mk] = bucket
        return bucket

    def add_user_delta(self, deltas: dict[str, dict[str, int]]) -> None:
        if not deltas:
            return
        with self._lock:
            bucket = self._current_bucket()
            users = bucket.setdefault("users", {})
            for email, t in deltas.items():
                em = str(email)
                slot = users.setdefault(em, {"up": 0, "down": 0})
                slot["up"] = int(slot.get("up", 0)) + int(t.get("uplink", 0))
                slot["down"] = int(slot.get("down", 0)) + int(t.get("downlink", 0))
            _atomic_write_json(self.path, self._data)

    def add_outbound_delta(self, deltas: dict[str, dict[str, int]]) -> None:
        if not deltas:
            return
        with self._lock:
            bucket = self._current_bucket()
            outbounds = bucket.setdefault("outbounds", {})
            for tag, t in deltas.items():
                tg = str(tag)
                slot = outbounds.setdefault(tg, {"up": 0, "down": 0})
                slot["up"] = int(slot.get("up", 0)) + int(t.get("uplink", 0))
                slot["down"] = int(slot.get("down", 0)) + int(t.get("downlink", 0))
            _atomic_write_json(self.path, self._data)

    def add_access_delta(self, domains: dict[str, int], ips: dict[str, int]) -> None:
        if not domains and not ips:
            return
        with self._lock:
            bucket = self._current_bucket()
            dom_bucket = bucket.setdefault("domains", {})
            ip_bucket = bucket.setdefault("ips", {})
            for host, n in domains.items():
                dom_bucket[str(host)] = int(dom_bucket.get(str(host), 0)) + int(n)
            for ip, n in ips.items():
                ip_bucket[str(ip)] = int(ip_bucket.get(str(ip), 0)) + int(n)
            _atomic_write_json(self.path, self._data)

    def get_access_log_offset(self) -> int:
        with self._lock:
            meta = self._data.setdefault("meta", {})
            return int(meta.get("access_log_offset", 0) or 0)

    def set_access_log_offset(self, offset: int) -> None:
        with self._lock:
            meta = self._data.setdefault("meta", {})
            meta["access_log_offset"] = int(offset)
            _atomic_write_json(self.path, self._data)

    def add_delta(self, deltas: dict[str, dict[str, int]]) -> None:
        """兼容旧调用：仅写入用户增量。"""
        self.add_user_delta(deltas)

    def get_totals_for_emails(self, emails: list[str]) -> tuple[dict[str, dict[str, int]], str | None]:
        mk = _month_key()
        with self._lock:
            err = self._last_poll_error
            raw_bucket = self._data.get("months", {}).get(mk, {})
            bucket = _normalize_month_bucket(raw_bucket)
            users = bucket.get("users", {})
            out: dict[str, dict[str, int]] = {}
            for em in emails:
                s = users.get(em, {"up": 0, "down": 0})
                out[em] = {
                    "up": int(s.get("up", 0)),
                    "down": int(s.get("down", 0)),
                }
            return out, err

    def get_service_stats(self, *, top_n: int = 8) -> dict[str, Any]:
        mk = _month_key()
        with self._lock:
            raw_bucket = self._data.get("months", {}).get(mk, {})
            bucket = _normalize_month_bucket(raw_bucket)

        outbounds_raw = bucket.get("outbounds", {})
        outbound_items: list[dict[str, Any]] = []
        for tag, t in outbounds_raw.items():
            up = int(t.get("up", 0))
            down = int(t.get("down", 0))
            total = up + down
            if total > 0:
                outbound_items.append({"tag": str(tag), "bytes": total, "bytes_up": up, "bytes_down": down})
        outbound_items.sort(key=lambda x: x["bytes"], reverse=True)

        domain_items = _top_count_items(bucket.get("domains", {}), top_n)
        ip_items = _top_count_items(bucket.get("ips", {}), top_n)

        return {
            "outbounds": outbound_items,
            "domains": domain_items,
            "ips": ip_items,
        }


def _top_count_items(raw: Any, top_n: int) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    pairs = [(str(k), int(v)) for k, v in raw.items() if int(v or 0) > 0]
    pairs.sort(key=lambda x: x[1], reverse=True)
    if len(pairs) <= top_n:
        return [{"label": k, "count": c} for k, c in pairs]
    head = pairs[:top_n]
    rest = sum(c for _, c in pairs[top_n:])
    items = [{"label": k, "count": c} for k, c in head]
    if rest > 0:
        items.append({"label": "其他", "count": rest})
    return items


_store: MonthlyTrafficStore | None = None


def get_store() -> MonthlyTrafficStore:
    global _store
    if _store is None:
        p = Path(os.environ.get("TRAFFIC_STORE_PATH", "/v2ray/panel_traffic_monthly.json")).resolve()
        _store = MonthlyTrafficStore(p)
    return _store
