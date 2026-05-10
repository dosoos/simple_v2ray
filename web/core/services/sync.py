from core.models import ProxyUser
from core.signals import suppress_proxy_revision


def apply_users_from_master(payload: dict) -> None:
    """从节点：用主节点返回的数据覆盖本地代理用户（按 uuid upsert）。"""
    if "users" not in payload:
        return
    users = payload.get("users") or []
    with suppress_proxy_revision():
        seen = set()
        for row in users:
            uid = row.get("uuid")
            if not uid:
                continue
            seen.add(uid)
            ProxyUser.objects.update_or_create(
                uuid=uid,
                defaults={
                    "label": row.get("label") or uid,
                    "alter_id": int(row.get("alter_id", 0)),
                    "level": int(row.get("level", 0)),
                    "enabled": bool(row.get("enabled", True)),
                    "traffic_limit_bytes": row.get("traffic_limit_bytes"),
                },
            )
        ProxyUser.objects.exclude(uuid__in=seen).delete()

