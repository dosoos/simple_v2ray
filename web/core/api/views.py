import json
import secrets
import uuid

from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from core import config
from core.models import GlobalRevision, Node, ProxyUser, TrafficSnapshot


def _raw_bearer(request) -> str | None:
    auth = request.headers.get("Authorization", "") or request.META.get(
        "HTTP_AUTHORIZATION", ""
    )
    if not auth.startswith("Bearer "):
        return None
    return auth[7:].strip()


def _resolve_node_from_bearer(request):
    """用 Authorization: Bearer 解析已启用的从节点。"""
    raw = _raw_bearer(request)
    if not raw:
        return None, JsonResponse({"error": "missing bearer token"}, status=401)
    try:
        node = Node.objects.get(bearer_token=raw)
    except Node.DoesNotExist:
        return None, JsonResponse({"error": "invalid bearer token"}, status=401)
    if not node.bearer_token:
        return None, JsonResponse({"error": "invalid bearer token"}, status=401)
    if node.role != Node.Role.SLAVE:
        return None, JsonResponse({"error": "not_slave_node"}, status=403)
    return node, None


@csrf_exempt
@require_GET
def sync_users(request):
    """主节点：返回当前用户列表与全局版本号（Bearer 鉴权）。"""
    if config.NODE_ROLE == "slave" and config.MASTER_URL:
        return JsonResponse({"error": "slave_readonly"}, status=403)

    node, err = _resolve_node_from_bearer(request)
    if err:
        return err
    if not node.enabled:
        return JsonResponse({"error": "node_disabled"}, status=403)

    try:
        since = int(request.GET.get("since", "0"))
    except ValueError:
        since = 0

    rev_obj = GlobalRevision.get_singleton()
    rev = rev_obj.revision
    if since >= rev:
        return JsonResponse({"revision": rev, "unchanged": True})

    users = list(
        ProxyUser.objects.all().values(
            "uuid",
            "label",
            "alter_id",
            "level",
            "enabled",
            "traffic_limit_bytes",
        )
    )
    for u in users:
        u["uuid"] = str(u["uuid"])
    return JsonResponse({"revision": rev, "users": users})


@csrf_exempt
@require_POST
def sync_traffic(request):
    """主节点：接收从节点上报的流量快照（Bearer 鉴权）。"""
    if config.NODE_ROLE == "slave":
        return JsonResponse({"error": "not_master"}, status=403)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    samples = body.get("samples", [])
    if not isinstance(samples, list):
        return JsonResponse({"error": "bad payload"}, status=400)

    node, err = _resolve_node_from_bearer(request)
    if err:
        return err
    if not node.enabled:
        return JsonResponse({"error": "node_disabled"}, status=403)

    node.last_heartbeat = timezone.now()
    node.save(update_fields=["last_heartbeat"])

    bulk = []
    for item in samples:
        uid = item.get("user_uuid")
        if not uid:
            continue
        try:
            user = ProxyUser.objects.get(uuid=uid)
        except ProxyUser.DoesNotExist:
            continue
        rec_at = item.get("recorded_at")
        dt = parse_datetime(rec_at) if rec_at else timezone.now()
        if dt is None:
            dt = timezone.now()
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        bulk.append(
            TrafficSnapshot(
                user=user,
                node=node,
                recorded_at=dt,
                uplink_bytes=int(item.get("uplink_bytes", 0)),
                downlink_bytes=int(item.get("downlink_bytes", 0)),
            )
        )
    TrafficSnapshot.objects.bulk_create(bulk, batch_size=500)

    return JsonResponse({"ok": True, "stored": len(bulk)})


def _new_bearer() -> str:
    return secrets.token_urlsafe(48)


@csrf_exempt
@require_POST
def nodes_join(request):
    """主节点：从节点登记。凭 node_uuid + name 领取/刷新 bearer_token（撤销后重新颁发）。"""
    if config.NODE_ROLE == "slave":
        return JsonResponse({"error": "not_master"}, status=403)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    name = (body.get("name") or "").strip()
    uid = (body.get("node_uuid") or body.get("token") or "").strip()
    base_url = (body.get("base_url") or "").strip()
    if not name or not uid:
        return JsonResponse({"error": "bad payload"}, status=400)

    try:
        nu = uuid.UUID(uid)
    except ValueError:
        return JsonResponse({"error": "bad node_uuid"}, status=400)

    node, created = Node.objects.get_or_create(
        node_uuid=nu,
        defaults={
            "name": name,
            "role": Node.Role.SLAVE,
            "is_local": False,
            "enabled": False,
            "base_url": base_url,
            "bearer_token": _new_bearer(),
        },
    )

    if not created and node.role == Node.Role.MASTER:
        return JsonResponse({"error": "cannot_join_master_node"}, status=409)

    if not created and not node.bearer_token:
        node.bearer_token = _new_bearer()

    node.name = name
    node.role = Node.Role.SLAVE
    node.is_local = False
    node.base_url = base_url
    node.last_heartbeat = timezone.now()
    node.save()

    return JsonResponse(
        {
            "ok": True,
            "name": node.name,
            "node_uuid": str(node.node_uuid),
            "bearer_token": node.bearer_token,
            "enabled": node.enabled,
        }
    )
