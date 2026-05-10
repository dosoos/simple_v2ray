import json
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand

from core import config
from core.models import Node


class Command(BaseCommand):
    help = "从节点：向主节点登记本机 name + node_uuid，领取 Authorization Bearer 令牌"

    def handle(self, *args, **options):
        if not config.MASTER_URL:
            self.stdout.write("未配置 MASTER_URL，跳过")
            return
        if config.NODE_ROLE != "slave":
            self.stdout.write("当前不是从节点（MASTER_URL 为空时默认为主节点），跳过")
            return

        node = Node.get_or_create_local()
        if not node.is_local:
            node.is_local = True
            node.save(update_fields=["is_local"])

        url = f"{config.MASTER_URL}/api/v1/nodes/join/"
        body = json.dumps(
            {
                "name": node.name,
                "node_uuid": str(node.node_uuid),
                "base_url": "",
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.stderr.write(self.style.ERROR(f"加入失败 HTTP {e.code}: {e.read()!r}"))
            return
        except urllib.error.URLError as e:
            self.stderr.write(self.style.ERROR(f"加入失败: {e}"))
            return

        bearer = payload.get("bearer_token")
        if bearer:
            node.bearer_token = bearer
            node.save(update_fields=["bearer_token"])

        self.stdout.write(self.style.SUCCESS(f"加入成功: {payload}"))
