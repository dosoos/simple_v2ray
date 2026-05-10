import json
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand
from django.utils import timezone

from core import config
from core.models import Node, ProxyUser
from core.v2ray_grpc import parse_user_totals, query_stats


class Command(BaseCommand):
    help = "从节点：将本机 V2Ray 统计上报到主节点"

    def handle(self, *args, **options):
        if not config.MASTER_URL:
            self.stdout.write("未配置 MASTER_URL，跳过")
            return
        if config.NODE_ROLE != "slave":
            self.stdout.write("非从节点角色，跳过上报")
            return

        try:
            stats = query_stats()
        except Exception as exc:
            self.stderr.write(self.style.WARNING(f"采集失败: {exc}"))
            return

        totals = parse_user_totals(stats)
        now = timezone.now()
        iso = now.isoformat()
        samples = []
        for user in ProxyUser.objects.filter(enabled=True):
            tup = totals.get(user.label)
            if not tup:
                continue
            up, down = tup
            samples.append(
                {
                    "user_uuid": str(user.uuid),
                    "uplink_bytes": up,
                    "downlink_bytes": down,
                    "recorded_at": iso,
                }
            )

        node = Node.get_or_create_local()
        if not node.is_local:
            node.is_local = True
            node.save(update_fields=["is_local"])
        if not node.bearer_token:
            self.stderr.write(
                self.style.ERROR(
                    "本机尚无 Bearer 令牌，请执行 join_master（主节点需已启用该节点）"
                )
            )
            return

        body = json.dumps({"samples": samples}).encode("utf-8")
        url = f"{config.MASTER_URL}/api/v1/sync/traffic/"
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {node.bearer_token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.stderr.write(self.style.ERROR(f"上报失败 HTTP {e.code}: {e.read()!r}"))
            return
        except urllib.error.URLError as e:
            self.stderr.write(self.style.ERROR(f"上报失败: {e}"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"已上报 {len(samples)} 条样本, 主节点存储 {data.get('stored', 0)}"
            )
        )

