import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from core import config
from core.models import Node, ProxyUser, TrafficSnapshot
from core.v2ray_grpc import parse_user_totals, query_stats

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "从 V2Ray Stats API 采集用户累计流量并写入快照表"

    def handle(self, *args, **options):
        try:
            stats = query_stats()
        except Exception as exc:
            logger.warning("statsquery skip: %s", exc)
            self.stderr.write(self.style.WARNING(f"采集跳过: {exc}"))
            return

        totals = parse_user_totals(stats)
        if not totals:
            self.stdout.write("无用户统计数据")
            return

        node = Node.get_or_create_local()
        if not node.is_local:
            node.is_local = True
            node.save(update_fields=["is_local"])

        now = timezone.now()
        bulk = []
        for user in ProxyUser.objects.filter(enabled=True):
            tup = totals.get(user.label)
            if not tup:
                continue
            up, down = tup
            bulk.append(
                TrafficSnapshot(
                    user=user,
                    node=node,
                    recorded_at=now,
                    uplink_bytes=up,
                    downlink_bytes=down,
                )
            )
        TrafficSnapshot.objects.bulk_create(bulk, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"写入 {len(bulk)} 条流量快照"))

