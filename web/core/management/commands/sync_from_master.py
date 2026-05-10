import json
import urllib.error
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

from core import config
from core.models import Node, SyncCursor
from core.services.sync import apply_users_from_master


class Command(BaseCommand):
    help = "从节点：从 MASTER_URL 拉取用户并更新本地数据库"

    def handle(self, *args, **options):
        if not config.MASTER_URL:
            self.stdout.write("未配置 MASTER_URL，跳过")
            return

        node = Node.get_or_create_local()
        if not node.is_local:
            node.is_local = True
            node.save(update_fields=["is_local"])

        if not node.bearer_token:
            self.stderr.write(
                self.style.ERROR(
                    "本机尚无 Bearer 令牌，请在主节点审核节点后执行 join_master 领取令牌"
                )
            )
            return

        cursor = SyncCursor.get_singleton()
        q = urllib.parse.urlencode({"since": cursor.last_user_revision})
        url = f"{config.MASTER_URL}/api/v1/sync/users/?{q}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {node.bearer_token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.stderr.write(self.style.ERROR(f"同步失败 HTTP {e.code}: {e.read()!r}"))
            return
        except urllib.error.URLError as e:
            self.stderr.write(self.style.ERROR(f"同步失败: {e}"))
            return

        rev = int(payload.get("revision", 0))
        if payload.get("unchanged"):
            self.stdout.write("用户列表无变更")
        else:
            users = payload.get("users") or []
            apply_users_from_master(payload)
            self.stdout.write(self.style.SUCCESS(f"已同步 {len(users)} 个用户"))

        cursor.last_user_revision = rev
        cursor.save(update_fields=["last_user_revision", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"游标更新为 revision={rev}"))
